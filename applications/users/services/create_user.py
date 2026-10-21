from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from applications.users.models import SecurityEventActionChoices, User
from applications.users.permissions.rules import can_assign_role
from applications.users.services._shared import record_event, validate_new_password, validate_user
from core.auth.roles import default_role


class CreateUserService:
    def __init__(self, *, actor: User) -> None:
        self.actor = actor

    @transaction.atomic
    def execute(self, *, username: str, email: str, first_name: str, last_name: str,
                password: str, role: str | None = None) -> User:
        actor = User.objects.select_for_update().get(pk=self.actor.pk)
        role = default_role() if role is None else role
        if not can_assign_role(actor=actor, role=role):
            raise PermissionDenied("No tiene permiso para crear usuarios con ese rol.")
        user = User(
            username=User.normalize_username(username), email=User.objects.normalize_email(email),
            first_name=first_name, last_name=last_name, role=role, last_password_change=timezone.now(),
        )
        validate_new_password(user=user, password=password)
        user.set_password(password)
        validate_user(user=user)
        user.save(user=actor)
        record_event(action=SecurityEventActionChoices.USER_CREATED, actor=actor, target=user)
        return user
