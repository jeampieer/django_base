from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from core.auth.permission_manager import PermissionManager


class IsSuperAdmin(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        return bool(request.user.is_authenticated and request.user.is_superuser)


class HasModelPolicy(BasePermission):
    """Cierra el acceso cuando el modelo/rol no tiene policy registrada."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if not request.user.is_authenticated:
            return False
        action = getattr(view, "policy_action", None)
        if action is None:
            action = "read" if getattr(view, "filter_view", False) else {
                "GET": "read", "HEAD": "read", "OPTIONS": "read",
                "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete",
            }.get(request.method, "read")
        manager = PermissionManager(request.user, view.model, action)
        if action == "read":
            return bool(manager.get_visible_fields())
        if action == "delete":
            # El callable se evalúa después, cuando el objeto ya está resuelto.
            return bool(manager.get_permissions().get("delete", False))
        return bool(manager.get_allowed_fields())
