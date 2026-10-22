from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from applications.users.models import SecurityEventActionChoices, User
from applications.users.permissions.rules import can_edit_profile
from applications.users.services._shared import (
    lock_users, record_event, revoke_browser_sessions, revoke_refreshes, validate_new_password,
)


class ChangePasswordService:
    def __init__(self, *, actor: User, target: User) -> None:
        self.actor, self.target = actor, target

    @transaction.atomic
    def execute(self, *, new_password: str, current_password: str | None = None) -> User:
        actor, target, _ = lock_users(actor=self.actor, target=self.target)
        if not can_edit_profile(actor=actor, target=target):
            raise PermissionDenied("No puede cambiar esta contraseña.")
        if actor.pk == target.pk and (not current_password or not target.check_password(current_password)):
            raise ValidationError({"current_password": "La contraseña actual no es correcta."})
        validate_new_password(user=target, password=new_password)
        if target.check_password(new_password):
            raise ValidationError({"new_password": "Debe ser distinta de la contraseña actual."})
        target.set_password(new_password)
        target.last_password_change = timezone.now()
        target.save(user=actor)
        revoke_refreshes(user=target)
        revoke_browser_sessions(user=target)
        record_event(action=SecurityEventActionChoices.PASSWORD_CHANGED, actor=actor, target=target)
        return target
