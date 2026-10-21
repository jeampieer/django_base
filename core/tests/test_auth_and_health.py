from unittest.mock import patch
from typing import Any

from django.contrib.auth import get_user_model
from django.db import OperationalError
from model_bakery import baker
import pytest
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_jwt_login_authenticated_request_and_refresh() -> None:
    user = baker.make(User, username="reader", is_active=True)
    user.set_password("example-password")
    user.save()
    client = APIClient()
    response = client.post(
        "/api/v1/auth/token/", {"username": "reader", "password": "example-password"}, format="json",
    )
    assert response.status_code == 200
    tokens = response.data["data"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/v1/example/labels/").status_code == 200
    refreshed = client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert refreshed.status_code == 200
    assert "access" in refreshed.data["data"]
    assert "refresh" not in refreshed.data["data"]
    replayed = client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert replayed.status_code == 200


def test_bad_refresh_returns_401_envelope() -> None:
    response = APIClient().post("/api/v1/auth/token/refresh/", {"refresh": "invalid"}, format="json")
    assert response.status_code == 401
    assert response.data["success"] is False


def test_invalid_login_returns_401() -> None:
    response = APIClient().post("/api/v1/auth/token/", {"username": "missing", "password": "bad"}, format="json")
    assert response.status_code == 401


def test_public_health_and_ping() -> None:
    client = APIClient()
    assert client.get("/health/ping/").data["data"]["message"] == "pong"
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.data["data"]["checks"] == {"database": "ok", "cache": "ok"}


def test_database_failure_returns_503_without_exposing_exception() -> None:
    with patch("core.api.views.health.connection.cursor", side_effect=OperationalError("sensitive-host")):
        response = APIClient().get("/health/")
    assert response.status_code == 503
    assert "sensitive-host" not in str(response.data)


def test_cors_only_allows_configured_origins(settings: Any) -> None:
    settings.CORS_ALLOWED_ORIGINS = ["https://client.example"]
    response = APIClient().options(
        "/api/v1/example/labels/", HTTP_ORIGIN="https://client.example",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )
    assert response["Access-Control-Allow-Origin"] == "https://client.example"
    response = APIClient().options(
        "/api/v1/example/labels/", HTTP_ORIGIN="https://unknown.example",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )
    assert "Access-Control-Allow-Origin" not in response


def test_openapi_is_json_and_protected(user_reader: User) -> None:
    client = APIClient()
    assert client.get("/api/schema/").status_code == 401
    client.force_authenticate(user_reader)
    assert client.get("/api/schema/").status_code == 403
    user_reader.is_superuser = True
    user_reader.save()
    response = client.get("/api/schema/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi+json")
    schema = response.data
    assert "/api/v1/example/entries/{id}/finalize/" in schema["paths"]
    assert "data" in schema["components"]["schemas"]["FinalizeEntryResponse"]["properties"]
