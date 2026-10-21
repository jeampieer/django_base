from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from applications.example.models import Entry, EntryStatusChoices


class CanFinalizeEntry(BasePermission):
    message = "Solo el autor puede finalizar su entrada activa en borrador."

    def has_object_permission(self, request: Request, view: Any, obj: Entry) -> bool:
        return bool(
            obj.created_by_id == request.user.pk and obj.is_active and obj.status == EntryStatusChoices.DRAFT
        )
