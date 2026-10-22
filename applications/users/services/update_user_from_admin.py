from typing import Any

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from applications.users.models import User
from applications.users.permissions.rules import can_access_admin
from applications.users.services._shared import lock_users
from applications.users.services.change_role import ChangeRoleService
from applications.users.services.set_user_active import SetUserActiveService
from applications.users.services.update_user import UpdateUserService


class UpdateUserFromAdminService:
    """Un envío del formulario nativo constituye una única operación atómica."""

    def __init__(self, *, actor: User, target: User) -> None:
        self.actor, self.target = actor, target

    @transaction.atomic
    def execute(self, *, changes: dict[str, Any]) -> User:
        actor, target, _ = lock_users(actor=self.actor, target=self.target, protect_superusers=True)
        if not can_access_admin(actor):
            raise PermissionDenied("No tiene acceso administrativo.")
        profile_fields = {"username", "email", "first_name", "last_name"}
        if set(changes) - (profile_fields | {"role", "is_active"}):
            raise ValidationError("El formulario no admite cambios de privilegios técnicos.")
        profile = {field: value for field, value in changes.items() if field in profile_fields}
        if profile:
            target = UpdateUserService(actor=actor, target=target).execute(changes=profile)
        if "role" in changes and changes["role"] != target.role:
            target = ChangeRoleService(actor=actor, target=target).execute(role=changes["role"])
        if "is_active" in changes:
            target = SetUserActiveService(actor=actor, target=target).execute(is_active=changes["is_active"])
        return target
