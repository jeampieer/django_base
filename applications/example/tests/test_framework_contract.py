from typing import Any

from django.contrib.auth import get_user_model
from model_bakery import baker
import pytest

from applications.example.models import Entry, Label
from applications.example.serializers.entry import EntryDetailSerializer, EntrySerializer
from applications.example.serializers.label import LabelSerializer
from core.api.filters import InvalidFilterFieldError, validate_filter_fields
from core.api.responses import ApiResponse
from core.auth.permission_manager import PermissionManager
from core.auth.policy import BasePolicy, ReadPolicy
from core.auth.registry import policy_registry
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_base_model_audit_soft_delete_and_restore(user_admin: User, user_reader: User) -> None:
    label = Label(name="Ejemplo")
    label.save_with_user(user_admin)
    assert label.created_by == user_admin
    label.name = "Otro"
    label.save_with_user(user_reader)
    assert label.updated_by == user_reader
    label.soft_delete(user=user_admin)
    label.refresh_from_db()
    assert not label.is_active
    label.restore(user=user_reader)
    label.refresh_from_db()
    assert label.is_active and label.updated_by == user_reader


def test_response_preserves_original_envelope() -> None:
    response = ApiResponse.created(data={"name": "Ejemplo"})
    assert response.status_code == 201
    assert response.data["success"] is True
    assert response.data["status"] == "success"
    assert "timestamp" in response.data["meta"]
    assert ApiResponse(code=999).status_code == 500


def test_missing_filter_allowlist_denies_fields() -> None:
    with pytest.raises(InvalidFilterFieldError):
        validate_filter_fields({"internal": "secret"}, [])


def test_response_fields_follow_policy(user_reader: User, monkeypatch: Any) -> None:
    manager = PermissionManager(user_reader, Label, "read")
    monkeypatch.setattr(manager, "get_visible_fields", lambda: ["id"])
    assert manager.filter_response_fields([{"id": 1, "secret": 2}]) == [{"id": 1}]


def test_serializers_do_not_query(django_assert_num_queries: Any) -> None:
    label = baker.make(Label)
    entry = baker.make(Entry, label=label)
    entry = Entry.objects.select_related("label").get(pk=entry.pk)
    with django_assert_num_queries(0):
        label_input = LabelSerializer(data={"name": "Nuevo"})
        assert label_input.is_valid()
        entry_input = EntrySerializer(data={"title": "Nuevo", "label": str(label.pk)})
        assert entry_input.is_valid()
        assert EntryDetailSerializer(entry).data["label_name"] == label.name


def test_missing_policy_denies_read(reader_client: APIClient, monkeypatch: Any) -> None:
    monkeypatch.delitem(policy_registry._policies, "example.Label")
    assert reader_client.get("/api/v1/example/labels/").status_code == 403


def test_all_crud_reads_apply_visible_fields(reader_client: APIClient, monkeypatch: Any) -> None:
    class RestrictedPolicy(BasePolicy):
        model_label = "example.Label"

        class authenticated_access:
            read = ReadPolicy(fields=["id"])

    monkeypatch.setitem(policy_registry._policies, "example.Label", RestrictedPolicy)
    label = baker.make(Label)
    responses = [
        reader_client.get("/api/v1/example/labels/"),
        reader_client.get(f"/api/v1/example/labels/{label.pk}/"),
        reader_client.post("/api/v1/example/labels/filter/", {}, format="json"),
    ]
    for response in responses:
        assert response.status_code == 200
        data = response.data["data"]
        item = data[0] if isinstance(data, list) else data
        assert set(item) == {"id"}
