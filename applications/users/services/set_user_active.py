from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from applications.users.models import SecurityEventActionChoices, SessionStatusChoices, User, UserSession
from applications.users.permissions.rules import can_manage_user
from applications.users.services._shared import lock_users, record_event, revoke_browser_sessions, revoke_refreshes


class SetUserActiveService:
    def __init__(self, *, actor: User, target: User) -> None:
        self.actor, self.target = actor, target

    @transaction.atomic
    def execute(self, *, is_active: bool) -> User:
        actor, target, locked = lock_users(actor=self.actor, target=self.target, protect_superusers=True)
        if not can_manage_user(actor=actor, target=target):
            raise PermissionDenied("No puede gestionar esta cuenta.")
        if not is_active and actor.pk == target.pk:
            raise ValidationError("No puede desactivar su propia cuenta.")
        if not is_active and target.is_superuser and target.is_active:
            if sum(user.is_superuser and user.is_active for user in locked) <= 1:
                raise ValidationError("Debe conservar al menos un superusuario activo.")
        if target.is_active == is_active:
            return target
        target.is_active = is_active
        target.save(user=actor)
        action = SecurityEventActionChoices.USER_ACTIVATED
        if not is_active:
            revoke_refreshes(user=target)
            revoke_browser_sessions(user=target)
            UserSession.objects.filter(user=target, status=SessionStatusChoices.SUCCESS, logout_at__isnull=True).update(
                logout_at=timezone.now(),
            )
            action = SecurityEventActionChoices.USER_DEACTIVATED
        record_event(action=action, actor=actor, target=target)
        return target
