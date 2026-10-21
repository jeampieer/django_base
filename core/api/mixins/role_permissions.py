from __future__ import annotations

from typing import Any

from django.db.models import Model, QuerySet

from core.auth.permission_manager import PermissionManager


class RolePermissionMixin:
    def get_permission_manager(self, action: str) -> PermissionManager:
        return PermissionManager(self.request.user, self.model, action)

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        return queryset.filter(self.get_permission_manager("read").get_query_filter())

    def validate_request_data(self, action: str) -> dict[str, Any]:
        return self.get_permission_manager(action).validate_data(self.request.data)

    def check_delete_permission(self, obj: Model | None = None) -> None:
        self.get_permission_manager("delete").check_delete_permission(target=obj)

    def filter_response_data(self, data: Any) -> Any:
        return self.get_permission_manager("read").filter_response_fields(data)
