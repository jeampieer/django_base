from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from applications.users.models import (
    SecurityEventActionChoices, SessionFailureChoices, SessionStatusChoices, User, UserSession,
)
from applications.users.services._shared import record_event
from applications.users.permissions.rules import can_access_admin


class AuthenticateUserService:
    def __init__(self, *, user: User | None) -> None:
        self.user = user

    def execute(self, *, attempted_username: str, password: str,
                ip_address: str | None = None, user_agent: str = "", admin_only: bool = False) -> User:
        # El error se lanza después del commit para conservar intentos fallidos y bloqueos.
        with transaction.atomic():
            result = self._authenticate(
                attempted_username=attempted_username, password=password, ip_address=ip_address,
                user_agent=user_agent, admin_only=admin_only,
            )
        if result is None:
            raise AuthenticationFailed("Credenciales incorrectas o cuenta no disponible.")
        return result

    def _authenticate(self, *, attempted_username: str, password: str,
                      ip_address: str | None, user_agent: str, admin_only: bool = False) -> User | None:
        user = User.objects.select_for_update().filter(pk=self.user.pk).first() if self.user else None
        now = timezone.now()
        reason = ""
        if user is None:
            make_password(password)
            reason = SessionFailureChoices.USER_NOT_FOUND
        elif not user.is_active:
            reason = SessionFailureChoices.INACTIVE_ACCOUNT
        elif user.locked_until and user.locked_until > now:
            reason = SessionFailureChoices.ACCOUNT_LOCKED
        elif user.role not in settings.USER_ROLES:
            reason = SessionFailureChoices.INVALID_ROLE
        elif not user.check_password(password):
            reason = SessionFailureChoices.INVALID_PASSWORD
            # Una nueva ventana de fallos comienza después de un bloqueo vencido.
            if user.locked_until and user.locked_until <= now:
                user.failed_login_attempts = 0
                user.locked_until = None
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.USER_LOCKOUT_THRESHOLD:
                user.locked_until = now + timedelta(seconds=settings.USER_LOCKOUT_SECONDS)
                record_event(action=SecurityEventActionChoices.ACCOUNT_LOCKED, actor=None, target=user,
                             ip_address=ip_address, extra={"failed_attempts": user.failed_login_attempts})
            user.save(update_fields=["failed_login_attempts", "locked_until", "modified"])
        elif admin_only and not can_access_admin(user):
            reason = SessionFailureChoices.ADMIN_ACCESS_DENIED
        UserSession.objects.create(
            user=user, attempted_username=attempted_username,
            status=SessionStatusChoices.FAILED if reason else SessionStatusChoices.SUCCESS,
            failure_reason=reason, ip_address=ip_address, user_agent=user_agent[:2000],
        )
        if reason:
            return None
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = now
        user.save(update_fields=["failed_login_attempts", "locked_until", "last_login", "modified"])
        return user
