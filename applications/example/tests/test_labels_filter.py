from model_bakery import baker
import pytest
from rest_framework.test import APIClient

from applications.example.models import Label

pytestmark = pytest.mark.django_db
URL = "/api/v1/example/labels/filter/"


def test_post_filter_uses_read_policy(reader_client: APIClient) -> None:
    baker.make(Label, name="Activa", is_active=True)
    baker.make(Label, name="Inactiva", is_active=False)
    response = reader_client.post(URL, {"filter": {"is_active": True}, "order_by": "name"}, format="json")
    assert response.status_code == 200
    assert [item["name"] for item in response.data["data"]] == ["Activa"]


@pytest.mark.parametrize("payload", [{"filter": {"password": "x"}}, {"filter": []}, {"order_by": []}, []])
def test_invalid_filters_return_400(reader_client: APIClient, payload: object) -> None:
    assert reader_client.post(URL, payload, format="json").status_code == 400


def test_get_is_not_supported(reader_client: APIClient) -> None:
    assert reader_client.get(URL).status_code == 405
