from model_bakery import baker
import pytest
from rest_framework.test import APIClient

from applications.users.models import User, UserSession
from .conftest import EXAMPLE_PASSWORD

pytestmark = pytest.mark.django_db
URL = "/api/v1/users/"


def test_manager_creates_member_without_technical_privileges(authenticated_client: APIClient, user_admin: User) -> None:
    response = authenticated_client.post(URL, {
        "username": "fictional.api", "email": "api@example.test", "first_name": "Example", "last_name": "API",
        "password": EXAMPLE_PASSWORD, "is_staff": True, "is_superuser": True, "created_by": str(user_admin.pk),
    }, format="json")
    assert response.status_code == 201, response.data
    user = User.objects.get(pk=response.data["data"]["id"])
    assert user.created_by == user_admin and user.check_password(EXAMPLE_PASSWORD)
    assert not user.is_staff and not user.is_superuser
    assert "password" not in response.data["data"]


def test_member_reads_only_self_in_list_filter_and_detail(
    reader_client: APIClient, user_reader: User, user_admin: User,
) -> None:
    response = reader_client.get(URL)
    assert [item["id"] for item in response.data["data"]] == [str(user_reader.pk)]
    response = reader_client.post(URL + "filter/", {}, format="json")
    assert [item["id"] for item in response.data["data"]] == [str(user_reader.pk)]
    assert reader_client.get(f"{URL}{user_admin.pk}/").status_code == 404
    assert reader_client.get(f"{URL}{user_reader.pk}/").status_code == 200


def test_member_profile_update_cannot_change_role_state_or_password(
    reader_client: APIClient, user_reader: User, user_admin: User,
) -> None:
    original_password = user_reader.password
    response = reader_client.patch(f"{URL}{user_reader.pk}/", {
        "first_name": "Updated", "role": user_admin.role, "is_active": False,
        "password": "ignored", "is_superuser": True,
    }, format="json")
    assert response.status_code == 200, response.data
    user_reader.refresh_from_db()
    assert user_reader.first_name == "Updated"
    assert user_reader.role != user_admin.role
    assert user_reader.is_active and not user_reader.is_superuser
    assert user_reader.password == original_password


def test_is_staff_alone_does_not_grant_management(reader_client: APIClient, user_reader: User) -> None:
    user_reader.is_staff = True
    user_reader.save()
    assert reader_client.post(URL, {}, format="json").status_code == 403


def test_delete_never_reactivates_and_activate_is_explicit(authenticated_client: APIClient, user_reader: User) -> None:
    url = f"{URL}{user_reader.pk}/"
    for _ in range(2):
        assert authenticated_client.delete(url).status_code == 200
        user_reader.refresh_from_db()
        assert user_reader.is_active is False
    assert authenticated_client.post(url + "activate/", {}, format="json").status_code == 200
    user_reader.refresh_from_db()
    assert user_reader.is_active is True
    assert authenticated_client.post(url + "deactivate/", {}, format="json").status_code == 200


def test_password_endpoint_requires_current_password(reader_client: APIClient, login_user: User) -> None:
    response = reader_client.post(URL + "change-password/", {"new_password": "Another-Fictional-9!q"}, format="json")
    assert response.status_code == 400
    response = reader_client.post(URL + "change-password/", {
        "current_password": EXAMPLE_PASSWORD, "new_password": "Another-Fictional-9!q",
    }, format="json")
    assert response.status_code == 200
    assert "new_password" not in response.data["data"]


def test_manager_reset_endpoint(authenticated_client: APIClient, user_reader: User) -> None:
    response = authenticated_client.post(
        f"{URL}{user_reader.pk}/change-password/", {"new_password": EXAMPLE_PASSWORD}, format="json",
    )
    assert response.status_code == 200, response.data


def test_role_endpoint_blocks_peer_assignment_and_allows_superuser(
    authenticated_client: APIClient, user_reader: User, user_superuser: User, user_admin: User,
) -> None:
    url = f"{URL}{user_reader.pk}/change-role/"
    assert authenticated_client.post(url, {"role": user_admin.role}, format="json").status_code == 403
    client = APIClient()
    client.force_authenticate(user_superuser)
    assert client.post(url, {"role": user_admin.role}, format="json").status_code == 200


def test_security_endpoints_are_read_only_and_scoped(
    reader_client: APIClient, user_reader: User, user_admin: User,
) -> None:
    baker.make(UserSession, user=user_reader, attempted_username=user_reader.username, status="SUCCESS")
    response = reader_client.get(f"{URL}{user_reader.pk}/sessions/")
    assert response.status_code == 200 and len(response.data["data"]) == 1
    assert reader_client.get(f"{URL}{user_reader.pk}/security-events/").status_code == 200
    assert reader_client.get(f"{URL}{user_admin.pk}/sessions/").status_code == 404
    assert reader_client.post(f"{URL}{user_reader.pk}/sessions/", {}, format="json").status_code == 405


def test_superuser_manages_peer_root_but_cannot_deactivate_self(user_superuser: User) -> None:
    peer = baker.make(User, role=user_superuser.role, is_superuser=True)
    client = APIClient()
    client.force_authenticate(user_superuser)
    response = client.patch(f"{URL}{peer.pk}/", {"first_name": "Updated"}, format="json")
    assert response.status_code == 200
    assert client.delete(f"{URL}{user_superuser.pk}/").status_code == 400
    assert client.post(f"{URL}{peer.pk}/deactivate/", {}, format="json").status_code == 200
    assert User.objects.filter(is_superuser=True, is_active=True).count() == 1
