from django.db import transaction
from django.utils import timezone

from applications.users.models import SecurityEventActionChoices, SessionStatusChoices, User, UserSession
from applications.users.services._shared import lock_users, record_event, revoke_browser_sessions, revoke_refreshes


class LogoutService:
    def __init__(self, *, user: User) -> None:
        self.user = user

    @transaction.atomic
    def execute(self) -> None:
        user, _, _ = lock_users(actor=self.user, target=self.user)
        revoke_refreshes(user=user)
        revoke_browser_sessions(user=user)
        UserSession.objects.filter(user=user, status=SessionStatusChoices.SUCCESS, logout_at__isnull=True).update(
            logout_at=timezone.now(),
        )
        record_event(action=SecurityEventActionChoices.LOGOUT, actor=user, target=user)
