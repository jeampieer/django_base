from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest
from rest_framework.exceptions import AuthenticationFailed

from applications.users.models import User
from applications.users.permissions.rules import can_access_admin
from applications.users.selectors.user import user_find_by_username
from applications.users.services.authenticate_user import AuthenticateUserService


class AdminAuthenticationBackend(ModelBackend):
    def authenticate(self, request: HttpRequest | None, username: str | None = None,
                     password: str | None = None, **kwargs: Any) -> User | None:
        if username is None or password is None:
            return None
        metadata = request.META if request else {}
        try:
            return AuthenticateUserService(user=user_find_by_username(username=username)).execute(
                attempted_username=username, password=password, admin_only=True,
                ip_address=metadata.get("REMOTE_ADDR"), user_agent=metadata.get("HTTP_USER_AGENT", ""),
            )
        except AuthenticationFailed:
            return None

    def user_can_authenticate(self, user: User) -> bool:
        return can_access_admin(user)
