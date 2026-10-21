"""Subconjunto tipado del PermissionManager original."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.db.models import Model, Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.auth.policy import AUDIT_FIELDS
from core.auth.registry import policy_registry
from core.auth.roles import get_role


class PermissionManager:
    def __init__(self, user: Any, model: type[Model], action: str) -> None:
        self.user = user
        self.model = model
        self.model_name = model._meta.label
        self.action = action
        self.role = get_role(user)

    def get_permissions(self) -> dict[str, Any]:
        if not self.user.is_active:
            return {}
        return policy_registry.get(self.role, self.model_name, superuser=self.user.is_superuser)

    def get_action_permissions(self) -> dict[str, Any]:
        return self.get_permissions().get(self.action, {})

    def get_query_filter(self) -> Q:
        query_filter = self.get_permissions().get("read", {}).get("query_filter")
        return query_filter(self.user) if callable(query_filter) else Q()

    def get_allowed_fields(self) -> list[str] | str:
        return self.get_action_permissions().get("allowed_fields", [])

    def get_visible_fields(self) -> list[str] | str:
        return self.get_permissions().get("read", {}).get("fields", [])

    def validate_data(self, data: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(data, Mapping):
            raise ValidationError("Se espera un objeto JSON; el CRUD de la plantilla no admite lotes.")
        allowed = self.get_allowed_fields()
        validated = {key: value for key, value in data.items() if allowed == "__all__" or key in allowed}
        readonly = self.get_action_permissions().get("readonly_fields", [])
        for key in list(validated):
            if key in AUDIT_FIELDS or (
                self.action == "update" and (
                    (readonly in ("__all__", "__all_except__") and allowed != "__all__" and key not in allowed)
                    or (isinstance(readonly, list) and key in readonly)
                )
            ):
                validated.pop(key)
        if self.action == "create":
            for key, resolver in self.get_action_permissions().get("auto_fields", {}).items():
                validated.setdefault(key, resolver(self.user))
        return validated

    def can_delete(self, target: Model | None = None) -> bool:
        permission = self.get_permissions().get("delete", False)
        if callable(permission):
            return bool(target is not None and permission(self.user, target))
        return bool(permission)

    def check_delete_permission(self, target: Model | None = None) -> None:
        if not self.can_delete(target):
            raise PermissionDenied("No tiene permiso para eliminar este recurso.")

    def filter_response_fields(self, data: Any) -> Any:
        visible = self.get_visible_fields()
        if visible == "__all__":
            return data
        if isinstance(data, list):
            return [self.filter_response_fields(item) for item in data]
        return {key: value for key, value in data.items() if key in visible}
