from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.management import call_command
from model_bakery import baker
import pytest

from applications.users.models import User
from core.auth.roles import default_role, role_choices

pytestmark = pytest.mark.django_db


def test_custom_user_uuid_audit_and_password_hash() -> None:
    user = User.objects.create_user(
        username="fictional.member", email="member@example.test", password="Fictional-Password-9!xO",
        first_name="Example", last_name="Member",
    )
    assert settings.AUTH_USER_MODEL == "users.User"
    assert isinstance(user.pk, UUID)
    assert user.role == default_role()
    assert user.created is not None and user.created_by is None
    assert user.check_password("Fictional-Password-9!xO")
    assert user.password != "Fictional-Password-9!xO"


def test_createsuperuser_command(monkeypatch: Any) -> None:
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "Fictional-Password-9!xO")
    call_command(
        "createsuperuser", username="fictional.root", email="root@example.test",
        first_name="Example", last_name="Root", interactive=False, verbosity=0,
    )
    user = User.objects.get(username="fictional.root")
    assert user.is_staff and user.is_superuser and user.is_active
    assert user.role == settings.USER_SUPERUSER_ROLE


def test_manager_refuses_invalid_superuser_flags() -> None:
    with pytest.raises(ValueError):
        User.objects.create_superuser(username="invalid", email="invalid@example.test", is_superuser=False)


def test_roles_can_be_replaced_without_editing_models_or_policies(settings: Any) -> None:
    settings.USER_ROLES = {
        "LEAD_EXAMPLE": {"label": "Líder ficticio", "level": 1, "permissions": ["users.manage", "example.write"]},
        "BASIC_EXAMPLE": {"label": "Básico ficticio", "level": 5, "permissions": []},
    }
    settings.USER_DEFAULT_ROLE = "BASIC_EXAMPLE"
    settings.USER_SUPERUSER_ROLE = "LEAD_EXAMPLE"
    user = User.objects.create_user(username="fictional.reconfigured", email="reconfigured@example.test")
    root = User.objects.create_superuser(username="fictional.reconfigured.root", email="reconfigured.root@example.test")
    assert user.role == "BASIC_EXAMPLE"
    assert root.role == "LEAD_EXAMPLE"
    assert dict(role_choices()) == {"LEAD_EXAMPLE": "Líder ficticio", "BASIC_EXAMPLE": "Básico ficticio"}
    baker.make(User, role="LEAD_EXAMPLE").full_clean(exclude=["created_by", "updated_by"])
