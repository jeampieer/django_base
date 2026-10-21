from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db.models import Model
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.mixins import RolePermissionMixin, SoftDeleteViewMixin
from core.api.responses import ApiResponse
from core.api.views.base import CustomApiBaseView


class CustomDetailView(RolePermissionMixin, SoftDeleteViewMixin, CustomApiBaseView):
    removable = False

    def get_object(self, pk: UUID) -> Model:
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(self.request, instance)
        return instance

    def get(self, request: Request, pk: UUID, *args: Any, **kwargs: Any) -> Response:
        output = self.get_serializer_class("paginated")(self.get_object(pk))
        return ApiResponse.success(data=self.filter_response_data(output.data))

    def put(self, request: Request, pk: UUID, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer_class()(
            self.get_object(pk), data=self.validate_request_data("update"), partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(updated_by=request.user)
        instance = self.get_queryset().get(pk=instance.pk)
        output = self.get_serializer_class("paginated")(instance)
        return ApiResponse.success(data=self.filter_response_data(output.data))

    def patch(self, request: Request, pk: UUID, *args: Any, **kwargs: Any) -> Response:
        return self.put(request, pk, *args, **kwargs)

    def delete(self, request: Request, pk: UUID, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object(pk)
        self.check_delete_permission(obj=instance)
        if self.removable:
            instance.delete()
        else:
            self.perform_soft_delete(instance, user=request.user)
        return ApiResponse.success(message="Recurso eliminado correctamente.")
