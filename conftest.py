from django.contrib.auth import get_user_model
from django.conf import settings
from model_bakery import baker
import pytest
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user_admin(db: None) -> User:
    role = next(code for code, config in settings.USER_ROLES.items() if "users.manage" in config["permissions"])
    return baker.make(User, role=role, is_staff=False, is_active=True)


@pytest.fixture
def user_reader(db: None) -> User:
    return baker.make(User, role=settings.USER_DEFAULT_ROLE, is_staff=False, is_active=True)


@pytest.fixture
def user_superuser(db: None) -> User:
    return baker.make(User, role=settings.USER_SUPERUSER_ROLE, is_superuser=True, is_staff=True, is_active=True)


@pytest.fixture
def authenticated_client(user_admin: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user_admin)
    return client


@pytest.fixture
def reader_client(user_reader: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user_reader)
    return client
