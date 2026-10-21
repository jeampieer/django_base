"""Validación genérica de policies, sin jerarquías de roles del negocio."""

from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.checks import Error, Tags, register

from core.auth.policy import AUDIT_FIELDS
from core.auth.registry import policy_registry


@register(Tags.security)
def check_policy_configuration(app_configs: Any, **kwargs: Any) -> list[Error]:
    errors: list[Error] = []
    roles = getattr(settings, "USER_ROLES", {})
    if not isinstance(roles, dict) or not roles:
        return [Error("USER_ROLES debe ser un catálogo no vacío.", id="core.E004")]
    for code, definition in roles.items():
        if (
            not isinstance(code, str) or not code or len(code) > 64 or not isinstance(definition, dict)
            or not isinstance(definition.get("label"), str) or not definition.get("label")
            or type(definition.get("level")) is not int or definition["level"] < 0
            or not isinstance(definition.get("permissions"), list)
            or not all(isinstance(item, str) and item for item in definition.get("permissions", []))
        ):
            errors.append(Error(f"Definición inválida de rol: {code}", id="core.E004"))
    if any(getattr(settings, key, None) not in roles for key in ("USER_DEFAULT_ROLE", "USER_SUPERUSER_ROLE")):
        errors.append(Error("Los roles por defecto y de bootstrap deben existir.", id="core.E005"))
    for key in ("USER_LOCKOUT_THRESHOLD", "USER_LOCKOUT_SECONDS"):
        if type(getattr(settings, key, None)) is not int or getattr(settings, key) <= 0:
            errors.append(Error(f"{key} debe ser un entero positivo.", id="core.E006"))
    if errors:
        return errors
    for label, policy in policy_registry.all_policies().items():
        try:
            model = apps.get_model(label)
        except (ValueError, LookupError):
            errors.append(Error(f"Modelo inválido en policy: {label}", id="core.E001"))
            continue
        fields = {item.name for item in model._meta.get_fields()}
        for role in roles:
            permissions = policy.to_role_dict(role)
            for action, option in (("create", "allowed_fields"), ("read", "fields"), ("update", "allowed_fields")):
                configured = permissions[action][option]
                if isinstance(configured, list) and set(configured) - fields:
                    errors.append(Error(f"Campos inválidos: {label}.{role}.{action}", id="core.E002"))
                if action != "read" and isinstance(configured, list) and set(configured) & set(AUDIT_FIELDS):
                    errors.append(Error(f"Auditoría editable: {label}.{role}.{action}", id="core.E003"))
    return errors
