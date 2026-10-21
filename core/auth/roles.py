"""Catálogo de roles configurable; no importa el modelo de usuario."""

from typing import Any

from django.conf import settings


def role_choices() -> list[tuple[str, str]]:
    roles = getattr(settings, "USER_ROLES", {})
    if not isinstance(roles, dict):
        return []
    # Los checks reportan definiciones inválidas; el campo no debe fallar antes.
    return [
        (code, definition.get("label", code)) for code, definition in roles.items()
        if isinstance(code, str) and isinstance(definition, dict)
        and isinstance(definition.get("label", code), str)
    ]


def default_role() -> str:
    return settings.USER_DEFAULT_ROLE


def get_role(user: Any) -> str:
    return getattr(user, "role", "")


def role_level(role: str) -> int:
    return settings.USER_ROLES.get(role, {}).get("level", -1)


def has_capability(user: Any, capability: str) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return capability in settings.USER_ROLES.get(get_role(user), {}).get("permissions", [])
