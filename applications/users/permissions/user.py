from typing import Any

from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request

from applications.users.permissions.rules import can_edit_profile, can_manage_user


class CanEditUser(BasePermission):
    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        return request.method in SAFE_METHODS or can_edit_profile(actor=request.user, target=obj)


class CanManageUser(BasePermission):
    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        return can_manage_user(actor=request.user, target=obj)
