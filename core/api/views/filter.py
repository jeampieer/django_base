from typing import Any

from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.mixins import RolePermissionMixin
from core.api.views.base import CustomApiBaseView


class CustomFilterView(RolePermissionMixin, CustomApiBaseView):
    filter_view = True

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if not isinstance(request.data, dict):
            raise ValidationError("El cuerpo debe ser un objeto JSON.")
        queryset = self.apply_filters_to_queryset(
            self.get_queryset(), request.data.get("filter"), request.data.get("exclude"),
            request.data.get("order_by"), request.data.get("q"),
        )
        return self.render_list(queryset, request)
