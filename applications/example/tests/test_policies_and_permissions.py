from types import SimpleNamespace

from django.contrib.auth import get_user_model
from model_bakery import baker
import pytest

from applications.example.models import Entry, EntryStatusChoices, Label
from applications.example.permissions.entry import CanFinalizeEntry
from core.auth.permission_manager import PermissionManager
from core.auth.registry import policy_registry

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_policies_registered_and_roles_generic(user_admin: User, user_reader: User) -> None:
    assert set(policy_registry.registered_labels()) == {"example.Label", "example.Entry", "users.User"}
    assert PermissionManager(user_admin, Label, "create").get_allowed_fields() == "__all__"
    assert PermissionManager(user_reader, Label, "create").get_allowed_fields() == []
    assert policy_registry.get("UNKNOWN", "example.Label")["read"]["fields"] == []
    assert policy_registry.get(user_admin.role, "missing.Model") == {}


def test_object_permission_requires_author_and_draft(user_admin: User, user_reader: User) -> None:
    entry = baker.make(Entry, label=baker.make(Label), created_by=user_admin)
    permission = CanFinalizeEntry()
    assert permission.has_object_permission(SimpleNamespace(user=user_admin), None, entry)
    assert not permission.has_object_permission(SimpleNamespace(user=user_reader), None, entry)
    entry.status = EntryStatusChoices.FINALIZED
    assert not permission.has_object_permission(SimpleNamespace(user=user_admin), None, entry)
