"""Pasos comunes internos a los casos de uso de usuarios."""

from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from applications.users.models import SecurityEvent, User


def lock_users(*, actor: User, target: User, protect_superusers: bool = False) -> tuple[User, User, list[User]]:
    query = Q(pk__in=[actor.pk, target.pk])
    if protect_superusers:
        query |= Q(is_superuser=True, is_active=True)
    # Un orden común evita interbloqueos entre operaciones sobre pares de usuarios.
    locked = list(User.objects.select_for_update().filter(query).order_by("pk"))
    by_pk = {user.pk: user for user in locked}
    if actor.pk not in by_pk or target.pk not in by_pk:
        raise User.DoesNotExist
    current_actor, current_target = by_pk[actor.pk], by_pk[target.pk]
    if not current_actor.is_active:
        raise PermissionDenied("La cuenta del actor está inactiva.")
    return current_actor, current_target, locked


def validate_user(*, user: User) -> None:
    try:
        user.full_clean(exclude=["created_by", "updated_by"], validate_unique=False, validate_constraints=False)
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict) from exc
    for field in ("username", "email"):
        if User.objects.exclude(pk=user.pk).filter(**{field: getattr(user, field)}).exists():
            raise ValidationError({field: "Ya existe un usuario con este valor."})


def validate_new_password(*, user: User, password: str) -> None:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc


def record_event(*, action: str, actor: User | None, target: User, ip_address: str | None = None,
                 extra: dict[str, Any] | None = None) -> None:
    SecurityEvent.objects.create(
        action=action, actor=actor, target_user=target, ip_address=ip_address, extra=extra or {},
    )


def revoke_refreshes(*, user: User) -> None:
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
