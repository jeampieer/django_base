from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from applications.users.models import SecurityEventActionChoices, User
from applications.users.permissions.rules import can_edit_profile
from applications.users.services._shared import lock_users, record_event, validate_user
from core.auth.roles import has_capability


class UpdateUserService:
    def __init__(self, *, actor: User, target: User) -> None:
        self.actor, self.target = actor, target

    @transaction.atomic
    def execute(self, *, changes: dict[str, str]) -> User:
        actor, target, _ = lock_users(actor=self.actor, target=self.target)
        if not can_edit_profile(actor=actor, target=target):
            raise PermissionDenied("No puede editar este perfil.")
        allowed = {"email", "first_name", "last_name"}
        if has_capability(actor, "users.manage"):
            allowed.add("username")
        if set(changes) - allowed:
            raise ValidationError("El perfil no admite cambios de rol, estado o privilegios.")
        for field, value in changes.items():
            setattr(target, field, User.objects.normalize_email(value) if field == "email" else value)
        validate_user(user=target)
        target.save(user=actor)
        record_event(action=SecurityEventActionChoices.PROFILE_UPDATED, actor=actor, target=target,
                     extra={"fields": sorted(changes)})
        return target
