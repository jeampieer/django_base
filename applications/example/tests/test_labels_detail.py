from uuid import uuid4

from django.contrib.auth import get_user_model
from model_bakery import baker
import pytest
from rest_framework.test import APIClient

from applications.example.models import Label

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_patch_preserves_audit(authenticated_client: APIClient, user_admin: User, user_reader: User) -> None:
    label = baker.make(Label, name="Antes", created_by=user_reader)
    response = authenticated_client.patch(
        f"/api/v1/example/labels/{label.pk}/",
        {"name": "Después", "created_by": user_admin.pk, "created": "2000-01-01T00:00:00Z"}, format="json",
    )
    assert response.status_code == 200
    label.refresh_from_db()
    assert label.name == "Después"
    assert label.created_by == user_reader
    assert label.updated_by == user_admin


def test_delete_deactivates_and_records_actor(authenticated_client: APIClient, user_admin: User) -> None:
    label = baker.make(Label)
    assert authenticated_client.delete(f"/api/v1/example/labels/{label.pk}/").status_code == 200
    label.refresh_from_db()
    assert label.is_active is False
    assert label.updated_by == user_admin


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_reader_cannot_mutate(reader_client: APIClient, method: str) -> None:
    label = baker.make(Label)
    response = getattr(reader_client, method)(f"/api/v1/example/labels/{label.pk}/", {}, format="json")
    assert response.status_code == 403


def test_missing_detail_returns_404(reader_client: APIClient) -> None:
    assert reader_client.get(f"/api/v1/example/labels/{uuid4()}/").status_code == 404
