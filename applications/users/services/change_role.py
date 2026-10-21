from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from applications.users.models import SecurityEventActionChoices, User
from applications.users.permissions.rules import can_assign_role, can_manage_user
from applications.users.services._shared import lock_users, record_event


class ChangeRoleService:
    def __init__(self, *, actor: User, target: User) -> None:
        self.actor, self.target = actor, target

    @transaction.atomic
    def execute(self, *, role: str) -> User:
        actor, target, _ = lock_users(actor=self.actor, target=self.target)
        if not can_manage_user(actor=actor, target=target) or not can_assign_role(actor=actor, role=role):
            raise PermissionDenied("No puede gestionar este usuario o asignar ese rol.")
        previous = target.role
        target.role = role
        target.save(user=actor)
        record_event(action=SecurityEventActionChoices.ROLE_CHANGED, actor=actor, target=target,
                     extra={"old_role": previous, "new_role": role})
        return target
