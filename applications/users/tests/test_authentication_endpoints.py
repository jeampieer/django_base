from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from applications.users.models import User, UserSession
from applications.users.services.set_user_active import SetUserActiveService
from django.conf import settings
from .conftest import EXAMPLE_PASSWORD

pytestmark = pytest.mark.django_db


def login(client: APIClient, user: User) -> dict[str, str]:
    response = client.post("/api/v1/auth/token/", {
        "username": user.username, "password": EXAMPLE_PASSWORD,
    }, format="json")
    assert response.status_code == 200, response.data
    return response.data["data"]


def test_login_me_refresh_verify_and_logout_all_sessions(login_user: User) -> None:
    client = APIClient()
    tokens = [login(client, login_user) for _ in range(2)]
    assert UserSession.objects.filter(user=login_user, status="SUCCESS").count() == 2
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens[0]['access']}")
    response = client.get("/api/v1/auth/me/")
    assert response.status_code == 200
    assert response.data["data"]["id"] == str(login_user.pk)
    assert "password" not in response.data["data"]
    response = client.post("/api/v1/auth/token/verify/", {"token": tokens[0]["access"]}, format="json")
    assert response.status_code == 200 and response.data["data"]["valid"]
    response = client.post("/api/v1/auth/token/refresh/", {"refresh": tokens[0]["refresh"]}, format="json")
    assert response.status_code == 200 and set(response.data["data"]) == {"access"}
    assert client.post("/api/v1/auth/logout/", {}, format="json").status_code == 200
    assert not UserSession.objects.filter(user=login_user, status="SUCCESS", logout_at__isnull=True).exists()
    for token in tokens:
        response = client.post("/api/v1/auth/token/refresh/", {"refresh": token["refresh"]}, format="json")
        assert response.status_code == 401
    # Se conserva la semántica del origen: logout revoca refresh, no access ya emitidos.
    assert client.get("/api/v1/auth/me/").status_code == 200


def test_failed_login_persists_audit_and_lockout(login_user: User, settings: Any) -> None:
    settings.USER_LOCKOUT_THRESHOLD = 1
    client = APIClient()
    response = client.post("/api/v1/auth/token/", {
        "username": login_user.username, "password": "fictional.wrong",
    }, format="json")
    assert response.status_code == 401
    login_user.refresh_from_db()
    assert login_user.locked_until is not None
    assert UserSession.objects.filter(user=login_user, status="FAILED").count() == 1
    response = client.post("/api/v1/auth/token/", {
        "username": login_user.username, "password": EXAMPLE_PASSWORD,
    }, format="json")
    assert response.status_code == 401


def test_deactivation_blocks_existing_access_and_refresh(user_admin: User, user_reader: User) -> None:
    refresh = RefreshToken.for_user(user_reader)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    SetUserActiveService(actor=user_admin, target=user_reader).execute(is_active=False)
    assert client.get("/api/v1/auth/me/").status_code == 401
    response = client.post("/api/v1/auth/token/refresh/", {"refresh": str(refresh)}, format="json")
    assert response.status_code == 401


def test_existing_access_uses_current_role_from_database(user_admin: User) -> None:
    token = RefreshToken.for_user(user_admin)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    User.objects.filter(pk=user_admin.pk).update(role=settings.USER_DEFAULT_ROLE)
    assert client.post("/api/v1/example/labels/", {"name": "Denied"}, format="json").status_code == 403
