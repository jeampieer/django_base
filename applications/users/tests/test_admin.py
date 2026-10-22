from datetime import timedelta
from typing import Any
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from applications.users.backends import AdminAuthenticationBackend
from applications.users.models import SecurityEvent, SessionFailureChoices, UserSession
from applications.users.services.change_password import ChangePasswordService
from applications.users.services.logout import LogoutService
from applications.users.services.set_user_active import SetUserActiveService
from applications.users.services.update_user_from_admin import UpdateUserFromAdminService
from .conftest import EXAMPLE_PASSWORD

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(user_superuser: User) -> Client:
    user_superuser.set_password(EXAMPLE_PASSWORD)
    user_superuser.save(update_fields=["password"])
    client = Client()
    response = client.post(reverse("admin:login"), {"username": user_superuser.username, "password": EXAMPLE_PASSWORD})
    assert response.status_code == 302
    return client


def profile_data(user: User, **changes: Any) -> dict[str, Any]:
    return {"username": user.username, "email": user.email, "first_name": user.first_name,
            "last_name": user.last_name, "role": user.role, "is_active": "on", **changes}


def test_native_login_index_and_registration(admin_client: Client, user_superuser: User) -> None:
    assert admin_client.get(reverse("admin:index")).status_code == 200
    assert {model._meta.label for model in admin.site._registry} == {
        "users.User", "users.UserSession", "users.SecurityEvent", "example.Label", "example.Entry",
    }
    assert UserSession.objects.get(user=user_superuser).status == "SUCCESS"
    assert not user_superuser.outstandingtoken_set.exists()
    assert admin_client.get("/api/v1/auth/me/").status_code == 401
    assert admin_client.get(reverse("admin:users_user_add")).status_code == 200


@pytest.mark.parametrize("attribute,value,reason", [
    ("is_staff", False, SessionFailureChoices.ADMIN_ACCESS_DENIED),
    ("is_superuser", False, SessionFailureChoices.ADMIN_ACCESS_DENIED),
    ("is_active", False, SessionFailureChoices.INACTIVE_ACCOUNT),
    ("role", "UNCONFIGURED", SessionFailureChoices.INVALID_ROLE),
])
def test_login_denials_are_audited(user_superuser: User, attribute: str, value: Any, reason: str) -> None:
    user_superuser.set_password(EXAMPLE_PASSWORD)
    setattr(user_superuser, attribute, value)
    user_superuser.save()
    client = Client()
    response = client.post(reverse("admin:login"), {"username": user_superuser.username, "password": EXAMPLE_PASSWORD})
    assert response.status_code == 200
    assert UserSession.objects.get().failure_reason == reason
    assert client.get(reverse("admin:index")).status_code == 302


def test_unknown_user_and_lockout_survive_failed_admin_login(user_superuser: User, settings: Any) -> None:
    client = Client()
    client.post(reverse("admin:login"), {"username": "missing", "password": "bad"})
    assert UserSession.objects.get().user is None
    user_superuser.set_password(EXAMPLE_PASSWORD)
    user_superuser.save()
    settings.USER_LOCKOUT_THRESHOLD = 1
    client.post(reverse("admin:login"), {"username": user_superuser.username, "password": "bad"})
    user_superuser.refresh_from_db()
    assert user_superuser.locked_until > timezone.now()
    response = client.post(reverse("admin:login"), {"username": user_superuser.username, "password": EXAMPLE_PASSWORD})
    assert response.status_code == 200
    assert UserSession.objects.filter(failure_reason="ACCOUNT_LOCKED").exists()
    assert SecurityEvent.objects.filter(action="ACCOUNT_LOCKED").count() == 1


def test_browser_csrf_is_required_for_login_and_writes(admin_client: Client, user_superuser: User) -> None:
    client = Client(enforce_csrf_checks=True)
    client.cookies = admin_client.cookies
    assert client.post(reverse("admin:login"), {"username": "x", "password": "x"}).status_code == 403
    assert client.post(reverse("admin:users_user_add"), {}).status_code == 403
    response = client.get(reverse("admin:users_user_add"))
    assert response.status_code == 200
    response = client.post(reverse("admin:users_user_add"), {
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        "username": "csrf.created", "email": "csrf@example.test", "first_name": "Example", "last_name": "CSRF",
        "role": user_superuser.role, "password1": EXAMPLE_PASSWORD, "password2": EXAMPLE_PASSWORD,
    })
    assert response.status_code == 302


@pytest.mark.parametrize("field", ["is_active", "is_staff", "is_superuser"])
def test_access_is_rechecked_for_existing_browser_session(admin_client: Client, user_superuser: User,
                                                          field: str) -> None:
    User.objects.filter(pk=user_superuser.pk).update(**{field: False})
    assert admin_client.get(reverse("admin:index")).status_code == 302


def test_create_user_hashes_password_and_ignores_forged_privileges(admin_client: Client, user_reader: User) -> None:
    response = admin_client.post(reverse("admin:users_user_add"), {
        **profile_data(user_reader, username="admin.created", email="admin-created@example.test"),
        "password1": EXAMPLE_PASSWORD, "password2": EXAMPLE_PASSWORD,
        "is_staff": "on", "is_superuser": "on", "created_by": str(user_reader.pk),
    })
    assert response.status_code == 302
    user = User.objects.get(username="admin.created")
    assert user.check_password(EXAMPLE_PASSWORD)
    assert user.created_by_id != user_reader.pk
    assert not user.is_staff and not user.is_superuser
    assert SecurityEvent.objects.filter(target_user=user, action="USER_CREATED").count() == 1


def test_service_validation_is_shown_and_does_not_retry(admin_client: Client, user_reader: User) -> None:
    with patch("applications.users.admin.UpdateUserFromAdminService.execute",
               side_effect=ValidationError({"email": "Conflicto detectado por service."})) as execute:
        response = admin_client.post(reverse("admin:users_user_change", args=[user_reader.pk]),
                                     profile_data(user_reader, email="other@example.test"))
    assert response.status_code == 200
    assert "Conflicto detectado" in response.content.decode()
    assert execute.call_count == 1
    user_reader.refresh_from_db()
    assert user_reader.email != "other@example.test"


def test_combined_profile_role_state_is_atomic(admin_client: Client, user_superuser: User) -> None:
    before = SecurityEvent.objects.count()
    data = profile_data(user_superuser, first_name="Must rollback")
    data.pop("is_active")
    response = admin_client.post(reverse("admin:users_user_change", args=[user_superuser.pk]), data)
    assert response.status_code == 200
    assert "propia cuenta" in response.content.decode()
    user_superuser.refresh_from_db()
    assert user_superuser.first_name != "Must rollback" and user_superuser.is_active
    assert SecurityEvent.objects.count() == before


def test_combined_user_change_records_each_operation(admin_client: Client, user_reader: User,
                                                     user_superuser: User) -> None:
    data = profile_data(user_reader, first_name="Updated", role=user_superuser.role)
    data.pop("is_active")
    response = admin_client.post(reverse("admin:users_user_change", args=[user_reader.pk]), data)
    assert response.status_code == 302
    user_reader.refresh_from_db()
    assert user_reader.first_name == "Updated" and user_reader.role == user_superuser.role
    assert not user_reader.is_active
    assert set(SecurityEvent.objects.filter(target_user=user_reader).values_list("action", flat=True)) == {
        "PROFILE_UPDATED", "ROLE_CHANGED", "USER_DEACTIVATED",
    }


@pytest.mark.parametrize("failure", [PermissionDenied("Denied"), IntegrityError("sensitive-db-information")])
def test_admin_handles_service_denial_and_integrity(admin_client: Client, user_reader: User,
                                                    failure: Exception) -> None:
    with patch("applications.users.admin.UpdateUserFromAdminService.execute", side_effect=failure):
        response = admin_client.post(reverse("admin:users_user_change", args=[user_reader.pk]),
                                     profile_data(user_reader))
    assert response.status_code == (403 if isinstance(failure, PermissionDenied) else 200)
    assert "sensitive-db-information" not in response.content.decode()


@pytest.mark.parametrize("route", ["admin:password_change", "admin:users_user_password"])
def test_own_password_requires_current_and_revokes_all_sessions(admin_client: Client, user_superuser: User,
                                                                route: str) -> None:
    other = Client()
    other.force_login(user_superuser)
    token = str(RefreshToken.for_user(user_superuser))
    url = reverse(route, args=[user_superuser.pk] if route.endswith("user_password") else [])
    page = admin_client.get(url)
    assert page.status_code == 200
    assert page.context["original"].pk == user_superuser.pk
    data = {"new_password1": "Changed-Fictional-8!xQ", "new_password2": "Changed-Fictional-8!xQ"}
    assert admin_client.post(url, data).status_code == 200
    response = admin_client.post(url, {**data, "current_password": EXAMPLE_PASSWORD})
    assert response.status_code == 302 and response.url == reverse("admin:login")
    user_superuser.refresh_from_db()
    assert user_superuser.check_password(data["new_password1"])
    assert other.get(reverse("admin:index")).status_code == 302
    with pytest.raises(TokenError):
        RefreshToken(token)


def test_password_form_mismatch_and_reset_other_user(admin_client: Client, user_reader: User) -> None:
    url = reverse("admin:users_user_password", args=[user_reader.pk])
    assert admin_client.get(url).status_code == 200
    response = admin_client.post(url, {"new_password1": EXAMPLE_PASSWORD, "new_password2": "different"})
    assert response.status_code == 200
    assert "no coinciden" in response.content.decode()
    response = admin_client.post(url, {"new_password1": "123", "new_password2": "123"})
    assert response.status_code == 200
    response = admin_client.post(url, {"new_password1": EXAMPLE_PASSWORD, "new_password2": EXAMPLE_PASSWORD})
    assert response.status_code == 302
    user_reader.refresh_from_db()
    assert user_reader.check_password(EXAMPLE_PASSWORD)


def test_admin_logout_is_post_only_and_revokes_other_sessions(admin_client: Client, user_superuser: User) -> None:
    other = Client()
    other.force_login(user_superuser)
    assert admin_client.get(reverse("admin:logout")).status_code == 405
    assert admin_client.post(reverse("admin:logout")).status_code == 200
    assert other.get(reverse("admin:index")).status_code == 302
    assert SecurityEvent.objects.filter(action="LOGOUT", target_user=user_superuser).exists()
    assert not UserSession.objects.filter(user=user_superuser, status="SUCCESS", logout_at__isnull=True).exists()


@pytest.mark.parametrize("operation", ["logout", "password", "deactivate"])
def test_services_revoke_browser_sessions_without_touching_other_users(user_superuser: User, operation: str) -> None:
    target = baker.make(User, is_active=True, is_staff=True, is_superuser=True)
    target.set_password(EXAMPLE_PASSWORD)
    target.save()
    own, unrelated = Client(), Client()
    own.force_login(target)
    unrelated.force_login(user_superuser)
    if operation == "logout":
        LogoutService(user=target).execute()
    elif operation == "password":
        ChangePasswordService(actor=user_superuser, target=target).execute(new_password="Changed-Fictional-8!xQ")
    else:
        SetUserActiveService(actor=user_superuser, target=target).execute(is_active=False)
        SetUserActiveService(actor=user_superuser, target=target).execute(is_active=True)
    assert own.get(reverse("admin:index")).status_code == 302
    assert unrelated.get(reverse("admin:index")).status_code == 200


def test_api_logout_revokes_admin_cookie(admin_client: Client, user_superuser: User) -> None:
    token = RefreshToken.for_user(user_superuser)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    assert client.post("/api/v1/auth/logout/", {}, format="json").status_code == 200
    assert admin_client.get(reverse("admin:index")).status_code == 302


@pytest.mark.parametrize("model_name", ["usersession", "securityevent"])
def test_audit_models_are_read_only_even_with_post(admin_client: Client, user_superuser: User,
                                                   model_name: str) -> None:
    obj = UserSession.objects.first() if model_name == "usersession" else baker.make(SecurityEvent)
    url = reverse(f"admin:users_{model_name}_change", args=[obj.pk])
    assert admin_client.get(url).status_code == 200
    assert admin_client.post(url, {"action": "LOGOUT"}).status_code == 403
    assert admin_client.get(reverse(f"admin:users_{model_name}_add")).status_code == 403
    delete_url = reverse(f"admin:users_{model_name}_delete", args=[obj.pk])
    assert admin_client.post(delete_url, {"post": "yes"}).status_code == 403


def test_admin_service_enforces_access_and_forbids_privilege_changes(user_superuser: User, user_reader: User) -> None:
    with pytest.raises(PermissionDenied):
        UpdateUserFromAdminService(actor=user_reader, target=user_reader).execute(changes={"first_name": "Denied"})
    with pytest.raises(ValidationError):
        UpdateUserFromAdminService(actor=user_superuser, target=user_reader).execute(changes={"is_staff": True})
    assert UpdateUserFromAdminService(actor=user_superuser, target=user_reader).execute(changes={}).pk == user_reader.pk


def test_admin_service_rechecks_actor_after_it_was_resolved(user_superuser: User, user_reader: User) -> None:
    User.objects.filter(pk=user_superuser.pk).update(is_superuser=False)
    with pytest.raises(PermissionDenied):
        UpdateUserFromAdminService(actor=user_superuser, target=user_reader).execute(changes={"first_name": "Denied"})


def test_admin_service_rolls_back_profile_when_role_is_invalid(user_superuser: User, user_reader: User) -> None:
    previous_name = user_reader.first_name
    before = SecurityEvent.objects.count()
    with pytest.raises(PermissionDenied):
        UpdateUserFromAdminService(actor=user_superuser, target=user_reader).execute(changes={
            "first_name": "Must rollback", "role": "UNCONFIGURED",
        })
    user_reader.refresh_from_db()
    assert user_reader.first_name == previous_name
    assert SecurityEvent.objects.count() == before


def test_expired_lock_resets_and_backend_handles_missing_credentials(user_superuser: User) -> None:
    user_superuser.set_password(EXAMPLE_PASSWORD)
    user_superuser.failed_login_attempts = 1
    user_superuser.locked_until = timezone.now() - timedelta(seconds=1)
    user_superuser.save()
    backend = AdminAuthenticationBackend()
    assert backend.authenticate(None) is None
    result = backend.authenticate(None, username=user_superuser.username, password=EXAMPLE_PASSWORD)
    assert result.pk == user_superuser.pk
    user_superuser.refresh_from_db()
    assert user_superuser.locked_until is None and user_superuser.failed_login_attempts == 0
    assert Session.objects.count() == 0
