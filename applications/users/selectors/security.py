from __future__ import annotations

from django.db.models import Q, QuerySet

from applications.users.models import SecurityEvent, User, UserSession


def sessions_for_user(*, user: User) -> QuerySet[UserSession]:
    return UserSession.objects.filter(user=user)


def security_events_for_user(*, user: User) -> QuerySet[SecurityEvent]:
    """Incluye participación como actor o destinatario y precarga ambas relaciones."""
    return SecurityEvent.objects.filter(Q(actor=user) | Q(target_user=user)).select_related("actor", "target_user")
