from typing import Any

from django.core.checks import run_checks
from model_bakery import baker
import pytest

from applications.users.models import SecurityEvent, SecurityEventActionChoices, User
from applications.users.permissions.rules import can_manage_user
from applications.users.permissions.user import CanManageUser
from applications.users.selectors.security import security_events_for_user
from applications.users.serializers.security import SecurityEventSerializer
from applications.users.serializers.user import CreateUserInputSerializer, UserDetailSerializer
from core.auth.permission_manager import PermissionManager

pytestmark = pytest.mark.django_db


def test_security_selector_includes_actor_and_target_without_n_plus_one(
    user_admin: User, user_reader: User, django_assert_num_queries: Any,
) -> None:
    first = baker.make(
        SecurityEvent, actor=user_admin, target_user=user_reader, action=SecurityEventActionChoices.ROLE_CHANGED,
    )
    second = baker.make(
        SecurityEvent, actor=user_reader, target_user=user_reader, action=SecurityEventActionChoices.LOGOUT,
    )
    baker.make(SecurityEvent, actor=user_admin, target_user=user_admin, action=SecurityEventActionChoices.LOGOUT)
    with django_assert_num_queries(1):
        events = list(security_events_for_user(user=user_reader))
    assert {event.pk for event in events} == {first.pk, second.pk}
    with django_assert_num_queries(0):
        data = SecurityEventSerializer(events, many=True).data
        assert all(item["actor_username"] for item in data)


def test_user_serializers_validate_and_represent_without_queries(
    user_reader: User, django_assert_num_queries: Any,
) -> None:
    with django_assert_num_queries(0):
        serializer = CreateUserInputSerializer(data={
            "username": "fictional.serializer", "email": "serializer@example.test", "first_name": "Example",
            "last_name": "Serializer", "password": "Fictional-Password-9!xO",
        })
        assert serializer.is_valid()
        assert UserDetailSerializer(user_reader).data["id"] == str(user_reader.pk)


def test_policy_scope_and_permissions_follow_configured_hierarchy(
    user_admin: User, user_reader: User, user_superuser: User,
) -> None:
    manager = PermissionManager(user_admin, User, "read")
    assert set(User.objects.filter(manager.get_query_filter()).values_list("pk", flat=True)) == {
        user_admin.pk, user_reader.pk,
    }
    assert can_manage_user(actor=user_admin, target=user_reader)
    assert not can_manage_user(actor=user_admin, target=user_superuser)
    assert PermissionManager(user_superuser, User, "create").get_allowed_fields()
    request = type("RequestStub", (), {"user": user_reader})()
    assert not CanManageUser().has_object_permission(request, None, user_admin)


def test_invalid_role_configuration_fails_checks(settings: Any) -> None:
    settings.USER_DEFAULT_ROLE = "UNCONFIGURED_EXAMPLE"
    assert any(item.id == "core.E005" for item in run_checks())


def test_malformed_role_definition_reports_check_instead_of_crashing(settings: Any) -> None:
    settings.USER_ROLES = {settings.USER_DEFAULT_ROLE: {"level": "invalid", "permissions": []}}
    assert any(item.id == "core.E004" for item in run_checks())
