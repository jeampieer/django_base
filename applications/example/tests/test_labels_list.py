from django.contrib.auth import get_user_model
from model_bakery import baker
import pytest
from rest_framework.test import APIClient

from applications.example.models import Label

User = get_user_model()

pytestmark = pytest.mark.django_db
URL = "/api/v1/example/labels/"


def test_requires_authentication() -> None:
    assert APIClient().get(URL).status_code == 401


def test_create_ignores_client_audit(authenticated_client: APIClient, user_admin: User, user_reader: User) -> None:
    response = authenticated_client.post(URL, {"name": "General", "created_by": user_reader.pk}, format="json")
    assert response.status_code == 201
    label = Label.objects.get(pk=response.data["data"]["id"])
    assert label.created_by == user_admin
    assert response.data["success"] is True


def test_list_paginates_and_searches(reader_client: APIClient) -> None:
    baker.make(Label, name="Visible")
    baker.make(Label, name="Otra")
    response = reader_client.get(URL, {"q": "Vis", "per_page": 1})
    assert response.status_code == 200
    assert [item["name"] for item in response.data["data"]] == ["Visible"]
    assert response.data["meta"]["pagination"]["total"] == 1


def test_reader_cannot_create(reader_client: APIClient) -> None:
    assert reader_client.post(URL, {"name": "Denegada"}, format="json").status_code == 403


def test_internal_filter_is_rejected(reader_client: APIClient) -> None:
    assert reader_client.get(URL, {"created_by__password": "x"}).status_code == 400


def test_invalid_data_has_error_envelope(authenticated_client: APIClient) -> None:
    response = authenticated_client.post(URL, {"name": ""}, format="json")
    assert response.status_code == 400
    assert response.data["success"] is False
    assert "name" in response.data["error"]["details"]


@pytest.mark.django_db(transaction=True)
def test_uniqueness_is_enforced_by_database(authenticated_client: APIClient) -> None:
    baker.make(Label, name="Duplicada")
    response = authenticated_client.post(URL, {"name": "Duplicada"}, format="json")
    assert response.status_code == 400
    assert Label.objects.filter(name="Duplicada").count() == 1
