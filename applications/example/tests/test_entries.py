from django.contrib.auth import get_user_model
from model_bakery import baker
import pytest
from rest_framework.test import APIClient

from applications.example.models import Entry, EntryStatusChoices, Label

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_create_cannot_bypass_service(authenticated_client: APIClient) -> None:
    label = baker.make(Label)
    response = authenticated_client.post("/api/v1/example/entries/", {
        "title": "Ejemplo", "label": str(label.pk), "status": "FINALIZED", "summary": "Ignorado",
    }, format="json")
    assert response.status_code == 201
    assert response.data["data"]["status"] == EntryStatusChoices.DRAFT
    assert response.data["data"]["summary"] == ""
    assert response.data["data"]["label_name"] == label.name


def test_finalize_endpoint(authenticated_client: APIClient, user_admin: User) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    response = authenticated_client.post(
        f"/api/v1/example/entries/{entry.pk}/finalize/", {"summary": "Listo"}, format="json",
    )
    assert response.status_code == 200
    assert response.data["data"]["status"] == EntryStatusChoices.FINALIZED
    assert response.data["data"]["finalized_at"]


def test_finalize_checks_object_permission(authenticated_client: APIClient, user_reader: User) -> None:
    entry = baker.make(Entry, created_by=user_reader, label=baker.make(Label))
    assert authenticated_client.post(
        f"/api/v1/example/entries/{entry.pk}/finalize/", {"summary": "Listo"}, format="json",
    ).status_code == 403


def test_statistics_endpoint(reader_client: APIClient) -> None:
    label = baker.make(Label)
    baker.make(Entry, label=label, _quantity=2)
    response = reader_client.get("/api/v1/example/labels/statistics/", {"minimum_entries": 2})
    assert response.status_code == 200
    assert response.data["data"][0]["entry_count"] == 2


def test_entry_detail_update_and_filter(authenticated_client: APIClient, reader_client: APIClient) -> None:
    label = baker.make(Label)
    entry = baker.make(Entry, label=label)
    url = f"/api/v1/example/entries/{entry.pk}/"
    response = authenticated_client.patch(url, {"title": "Actualizada"}, format="json")
    assert response.status_code == 200
    assert response.data["data"]["label_name"] == label.name
    assert reader_client.get(url).data["data"]["title"] == "Actualizada"
    assert reader_client.get("/api/v1/example/entries/").status_code == 200
    response = reader_client.post(
        "/api/v1/example/entries/filter/", {"filter": {"title": "Actualizada"}}, format="json",
    )
    assert len(response.data["data"]) == 1
