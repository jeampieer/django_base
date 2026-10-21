"""Predicados compartidos por permisos HTTP, policies y services; sin escrituras."""

from typing import Any

from django.conf import settings
from django.db.models import Q

from core.auth.roles import has_capability, role_level


def can_assign_role(*, actor: Any, role: str) -> bool:
    if role not in settings.USER_ROLES or not actor.is_active:
        return False
    return bool(actor.is_superuser or (
        has_capability(actor, "users.manage") and role_level(role) > role_level(actor.role)
    ))


def can_manage_user(*, actor: Any, target: Any) -> bool:
    if not actor.is_active:
        return False
    if actor.is_superuser:
        return True
    return bool(
        not target.is_superuser and has_capability(actor, "users.manage")
        and target.role in settings.USER_ROLES and role_level(target.role) > role_level(actor.role)
    )


def can_edit_profile(*, actor: Any, target: Any) -> bool:
    return bool(actor.is_active and (actor.pk == target.pk or can_manage_user(actor=actor, target=target)))


def visible_users_filter(actor: Any) -> Q:
    if actor.is_superuser:
        return Q()
    if has_capability(actor, "users.manage"):
        roles = [code for code in settings.USER_ROLES if role_level(code) > role_level(actor.role)]
        return Q(pk=actor.pk) | Q(role__in=roles, is_superuser=False)
    return Q(pk=actor.pk)
