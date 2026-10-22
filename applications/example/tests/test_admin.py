from typing import Any
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from model_bakery import baker
import pytest

from applications.example.models import Entry, EntryStatusChoices, Label

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(user_superuser: User) -> Client:
    client = Client()
    client.force_login(user_superuser)
    return client


def test_native_crud_records_actor_and_preserves_audit(admin_client: Client, user_superuser: User,
                                                       user_reader: User) -> None:
    assert admin_client.get(reverse("admin:example_label_add")).status_code == 200
    response = admin_client.post(reverse("admin:example_label_add"), {
        "name": "Native label", "is_active": "on", "created_by": str(user_reader.pk),
    })
    assert response.status_code == 302
    label = Label.objects.get(name="Native label")
    assert label.created_by == user_superuser
    url = reverse("admin:example_label_change", args=[label.pk])
    response = admin_client.get(url)
    assert response.status_code == 200
    assert response.content.decode().count("Auditoría") == 1
    response = admin_client.post(url, {"name": "Changed", "updated_by": str(user_reader.pk)})
    assert response.status_code == 302
    label.refresh_from_db()
    assert label.name == "Changed" and not label.is_active
    assert label.created_by == user_superuser and label.updated_by == user_superuser


def test_entry_crud_cannot_write_finalization_fields(admin_client: Client, user_superuser: User) -> None:
    label = baker.make(Label)
    assert admin_client.get(reverse("admin:example_entry_add")).status_code == 200
    response = admin_client.post(reverse("admin:example_entry_add"), {
        "title": "Native entry", "label": str(label.pk), "is_active": "on",
        "status": "FINALIZED", "summary": "Bypass", "finalized_at": "2026-01-01T00:00:00Z",
    })
    assert response.status_code == 302
    entry = Entry.objects.get(title="Native entry")
    assert entry.status == "DRAFT" and not entry.summary and entry.finalized_at is None
    assert entry.created_by == user_superuser
    response = admin_client.post(reverse("admin:example_entry_change", args=[entry.pk]), {
        "title": "Updated", "label": str(label.pk), "is_active": "on", "status": "FINALIZED",
    })
    assert response.status_code == 302
    entry.refresh_from_db()
    assert entry.title == "Updated" and entry.status == "DRAFT"


def test_finalize_uses_service_and_native_form(admin_client: Client, user_superuser: User) -> None:
    entry = baker.make(Entry, created_by=user_superuser, label__is_active=True)
    url = reverse("admin:example_entry_finalize", args=[entry.pk])
    detail = admin_client.get(reverse("admin:example_entry_change", args=[entry.pk]))
    assert url in detail.content.decode()
    response = admin_client.get(url)
    assert response.status_code == 200
    assert "admin/change_form.html" in [template.name for template in response.templates]
    assert admin_client.post(url, {"summary": "Final summary"}).status_code == 302
    entry.refresh_from_db()
    assert entry.status == EntryStatusChoices.FINALIZED
    assert entry.summary == "Final summary" and entry.updated_by == user_superuser
    response = admin_client.post(url, {"summary": "A second finalization"})
    assert response.status_code == 200
    assert "borrador" in response.content.decode()


def test_finalize_still_requires_author(admin_client: Client, user_reader: User) -> None:
    entry = baker.make(Entry, created_by=user_reader)
    response = admin_client.post(reverse("admin:example_entry_finalize", args=[entry.pk]), {"summary": "Denied"})
    assert response.status_code == 403
    entry.refresh_from_db()
    assert entry.status == "DRAFT" and entry.finalized_at is None


def test_finalize_rejects_inactive_label(admin_client: Client, user_superuser: User) -> None:
    entry = baker.make(Entry, created_by=user_superuser, label__is_active=False)
    response = admin_client.post(reverse("admin:example_entry_finalize", args=[entry.pk]), {"summary": "Denied"})
    assert response.status_code == 200
    assert "etiqueta debe estar activa" in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == "DRAFT"


@pytest.mark.parametrize("model", [Label, Entry])
def test_no_hard_delete_or_bulk_actions(admin_client: Client, model: Any) -> None:
    obj = baker.make(model)
    prefix = f"admin:example_{model._meta.model_name}"
    assert admin_client.post(reverse(f"{prefix}_delete", args=[obj.pk]), {"post": "yes"}).status_code == 403
    admin_client.post(reverse(f"{prefix}_changelist"), {"action": "delete_selected", "_selected_action": str(obj.pk)})
    assert model.objects.filter(pk=obj.pk).exists()


def test_missing_operation_object_and_unsupported_methods(admin_client: Client) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    assert admin_client.get(reverse("admin:example_entry_finalize", args=[missing])).status_code == 404
    assert admin_client.put(reverse("admin:example_label_add"), {}).status_code == 405
    entry = baker.make(Entry)
    assert admin_client.put(reverse("admin:example_entry_finalize", args=[entry.pk]), {}).status_code == 405


def test_duplicate_label_shows_form_error(admin_client: Client) -> None:
    label = baker.make(Label)
    response = admin_client.post(reverse("admin:example_label_add"), {"name": label.name, "is_active": "on"})
    assert response.status_code == 200
    assert Label.objects.filter(name=label.name).count() == 1


def test_native_save_has_no_outer_transaction(admin_client: Client, user_superuser: User) -> None:
    # pytest ya envuelve este test en atomic; el adaptador no debe añadir otro nivel.
    from django.db import connection
    from applications.example.admin import LabelAdmin
    original = LabelAdmin.save_model
    initial_depth = len(connection.atomic_blocks)
    depths = []

    def save(self: Any, request: Any, obj: Any, form: Any, change: bool) -> None:
        depths.append(len(connection.atomic_blocks))
        original(self, request, obj, form, change)

    with patch.object(LabelAdmin, "save_model", save):
        response = admin_client.post(reverse("admin:example_label_add"), {"name": "No outer atomic", "is_active": "on"})
    assert response.status_code == 302 and depths == [initial_depth]
