from datetime import timedelta
from typing import Any

from django.utils import timezone
import pytest
from rest_framework.exceptions import AuthenticationFailed

from applications.users.models import (
    SecurityEvent, SecurityEventActionChoices, SessionFailureChoices, User, UserSession,
)
from applications.users.services.login import LoginService
from .conftest import EXAMPLE_PASSWORD

pytestmark = pytest.mark.django_db


def test_unknown_login_is_audited_without_user() -> None:
    with pytest.raises(AuthenticationFailed):
        LoginService(user=None).execute(attempted_username="fictional.missing", password="fictional")
    session = UserSession.objects.get()
    assert session.user is None
    assert session.failure_reason == SessionFailureChoices.USER_NOT_FOUND


def test_failed_attempts_commit_and_lockout_is_configurable(login_user: User, settings: Any) -> None:
    settings.USER_LOCKOUT_THRESHOLD = 2
    settings.USER_LOCKOUT_SECONDS = 60
    for _ in range(2):
        with pytest.raises(AuthenticationFailed):
            LoginService(user=login_user).execute(attempted_username=login_user.username, password="fictional.wrong")
    login_user.refresh_from_db()
    assert login_user.failed_login_attempts == 2
    assert login_user.locked_until > timezone.now()
    with pytest.raises(AuthenticationFailed):
        LoginService(user=login_user).execute(attempted_username=login_user.username, password=EXAMPLE_PASSWORD)
    assert UserSession.objects.count() == 3
    assert UserSession.objects.filter(failure_reason=SessionFailureChoices.ACCOUNT_LOCKED).count() == 1
    assert SecurityEvent.objects.filter(action=SecurityEventActionChoices.ACCOUNT_LOCKED).count() == 1


def test_success_after_expiry_resets_lock_and_updates_last_login(login_user: User) -> None:
    User.objects.filter(pk=login_user.pk).update(
        failed_login_attempts=10, locked_until=timezone.now() - timedelta(seconds=1),
    )
    result = LoginService(user=login_user).execute(attempted_username=login_user.username, password=EXAMPLE_PASSWORD)
    result.user.refresh_from_db()
    assert result.user.failed_login_attempts == 0 and result.user.locked_until is None
    assert result.user.last_login is not None
    assert result.access and result.refresh


def test_inactive_user_is_audited_without_incrementing_failures(login_user: User) -> None:
    User.objects.filter(pk=login_user.pk).update(is_active=False)
    with pytest.raises(AuthenticationFailed):
        LoginService(user=login_user).execute(attempted_username=login_user.username, password=EXAMPLE_PASSWORD)
    assert UserSession.objects.get().failure_reason == SessionFailureChoices.INACTIVE_ACCOUNT
    login_user.refresh_from_db()
    assert login_user.failed_login_attempts == 0
