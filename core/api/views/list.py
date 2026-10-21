from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from core.api.mixins import RolePermissionMixin
from core.api.responses import ApiResponse
from core.api.views.base import CustomApiBaseView


class CustomListView(RolePermissionMixin, CustomApiBaseView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        reserved = {"order_by", "page", "per_page", "q"}
        filters = {
            key: value for key, value in request.query_params.items()
            if key not in reserved and not key.startswith("exclude__")
        }
        excludes = {
            key.removeprefix("exclude__"): value for key, value in request.query_params.items()
            if key.startswith("exclude__")
        }
        queryset = self.apply_filters_to_queryset(
            self.get_queryset(), filters, excludes,
            request.query_params.get("order_by"), request.query_params.get("q"),
        )
        return self.render_list(queryset, request)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer_class()(
            data=self.validate_request_data("create"), context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by=request.user)
        instance = self.get_queryset().get(pk=instance.pk)
        output = self.get_serializer_class("paginated")(instance)
        return ApiResponse.created(data=self.filter_response_data(output.data))
