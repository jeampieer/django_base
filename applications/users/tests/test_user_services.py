from unittest.mock import patch

from django.conf import settings
from model_bakery import baker
import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from applications.users.models import SecurityEvent, SecurityEventActionChoices, User
from applications.users.services.change_password import ChangePasswordService
from applications.users.services.change_role import ChangeRoleService
from applications.users.services.create_user import CreateUserService
from applications.users.services.set_user_active import SetUserActiveService
from applications.users.services.update_user import UpdateUserService
from .conftest import EXAMPLE_PASSWORD

pytestmark = pytest.mark.django_db


def test_create_user_service_hashes_and_audits(user_admin: User) -> None:
    user = CreateUserService(actor=user_admin).execute(
        username="fictional.created", email="created@example.test", first_name="Example", last_name="Created",
        password=EXAMPLE_PASSWORD,
    )
    assert user.check_password(EXAMPLE_PASSWORD)
    assert user.created_by == user_admin
    assert not user.is_staff and not user.is_superuser
    assert SecurityEvent.objects.filter(target_user=user, action=SecurityEventActionChoices.USER_CREATED).exists()


def test_creation_rejects_peer_role_and_member_actor(user_admin: User, user_reader: User) -> None:
    data = dict(username="fictional.denied", email="denied@example.test", first_name="Example", last_name="Denied",
                password=EXAMPLE_PASSWORD)
    with pytest.raises(PermissionDenied):
        CreateUserService(actor=user_admin).execute(role=user_admin.role, **data)
    with pytest.raises(PermissionDenied):
        CreateUserService(actor=user_reader).execute(**data)


def test_creation_and_audit_are_atomic(user_admin: User) -> None:
    with (
        patch("applications.users.services.create_user.record_event", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        CreateUserService(actor=user_admin).execute(
            username="fictional.rollback", email="rollback@example.test", first_name="Example", last_name="Rollback",
            password=EXAMPLE_PASSWORD,
        )
    assert not User.objects.filter(username="fictional.rollback").exists()


def test_profile_update_rejects_privilege_fields_and_outside_scope(user_admin: User, user_reader: User) -> None:
    with pytest.raises(ValidationError):
        UpdateUserService(actor=user_reader, target=user_reader).execute(changes={"role": user_admin.role})
    with pytest.raises(PermissionDenied):
        UpdateUserService(actor=user_reader, target=user_admin).execute(changes={"first_name": "Denied"})


def test_profile_update_preserves_creator_and_tracks_actor(user_admin: User, user_reader: User) -> None:
    result = UpdateUserService(actor=user_admin, target=user_reader).execute(changes={"first_name": "Updated"})
    assert result.first_name == "Updated"
    assert result.updated_by == user_admin


def test_role_change_enforces_assignment_hierarchy(user_admin: User, user_reader: User, user_superuser: User) -> None:
    with pytest.raises(PermissionDenied):
        ChangeRoleService(actor=user_admin, target=user_reader).execute(role=user_admin.role)
    changed = ChangeRoleService(actor=user_superuser, target=user_reader).execute(role=user_admin.role)
    assert changed.role == user_admin.role
    assert SecurityEvent.objects.filter(target_user=changed, action=SecurityEventActionChoices.ROLE_CHANGED).exists()


def test_password_change_requires_current_and_revokes_all_refreshes(login_user: User) -> None:
    tokens = [str(RefreshToken.for_user(login_user)) for _ in range(2)]
    with pytest.raises(ValidationError):
        ChangePasswordService(actor=login_user, target=login_user).execute(new_password="Another-Fictional-7!p")
    changed = ChangePasswordService(actor=login_user, target=login_user).execute(
        new_password="Another-Fictional-7!p", current_password=EXAMPLE_PASSWORD,
    )
    assert changed.check_password("Another-Fictional-7!p")
    assert changed.last_password_change is not None
    for token in tokens:
        with pytest.raises(TokenError):
            RefreshToken(token)


def test_manager_resets_lower_role_password_without_old_password(user_admin: User, user_reader: User) -> None:
    result = ChangePasswordService(actor=user_admin, target=user_reader).execute(new_password=EXAMPLE_PASSWORD)
    assert result.check_password(EXAMPLE_PASSWORD)


@pytest.mark.parametrize("new_password", ["123", EXAMPLE_PASSWORD])
def test_weak_or_unchanged_password_is_rejected(login_user: User, new_password: str) -> None:
    with pytest.raises(ValidationError):
        ChangePasswordService(actor=login_user, target=login_user).execute(
            current_password=EXAMPLE_PASSWORD, new_password=new_password,
        )


def test_state_changes_are_explicit_idempotent_and_revoke_refreshes(user_admin: User, user_reader: User) -> None:
    token = str(RefreshToken.for_user(user_reader))
    for _ in range(2):
        result = SetUserActiveService(actor=user_admin, target=user_reader).execute(is_active=False)
        assert result.is_active is False
    assert SecurityEvent.objects.filter(
        target_user=user_reader, action=SecurityEventActionChoices.USER_DEACTIVATED,
    ).count() == 1
    with pytest.raises(TokenError):
        RefreshToken(token)
    assert SetUserActiveService(actor=user_admin, target=user_reader).execute(is_active=True).is_active


def test_superuser_and_self_deactivation_are_protected(user_admin: User, user_superuser: User) -> None:
    with pytest.raises(PermissionDenied):
        SetUserActiveService(actor=user_admin, target=user_superuser).execute(is_active=False)
    with pytest.raises(ValidationError):
        SetUserActiveService(actor=user_superuser, target=user_superuser).execute(is_active=False)
    assert User.objects.filter(is_superuser=True, is_active=True).count() == 1


def test_stale_actor_is_reloaded_before_authorization(user_admin: User, user_reader: User) -> None:
    User.objects.filter(pk=user_admin.pk).update(role=settings.USER_DEFAULT_ROLE)
    with pytest.raises(PermissionDenied):
        ChangePasswordService(actor=user_admin, target=user_reader).execute(new_password=EXAMPLE_PASSWORD)


def test_manager_cannot_manage_peer(user_admin: User) -> None:
    peer = baker.make(User, role=user_admin.role)
    with pytest.raises(PermissionDenied):
        SetUserActiveService(actor=user_admin, target=peer).execute(is_active=False)
