"""Selección de serializers, filtros y paginación del core original."""

from __future__ import annotations

from typing import Any

from django.db.models import Model, Q, QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from core.api.filters import validate_filter_fields, validate_order_by_field
from core.api.pagination import CustomPagination
from core.api.responses import ApiResponse
from core.auth.permissions import HasModelPolicy


class CustomApiBaseView(APIView, CustomPagination):
    permission_classes = [IsAuthenticated, HasModelPolicy]
    model: type[Model]
    serializer: type[BaseSerializer]
    detail_serializer: type[BaseSerializer] | None = None
    search: tuple[str, ...] = ()
    allowed_filters: tuple[str, ...] = ()
    allowed_excludes: tuple[str, ...] = ()
    allowed_order_by: tuple[str, ...] = ("created",)
    required_pagination = False

    @property
    def serializer_class(self) -> type[BaseSerializer]:
        return self.get_serializer_class("paginated" if self.request.method == "GET" else "default")

    def get_serializer_class(self, context: str = "default") -> type[BaseSerializer]:
        if context == "paginated" and self.detail_serializer:
            return self.detail_serializer
        return self.serializer

    def get_queryset(self) -> QuerySet:
        return self.model._default_manager.all()

    def get_pagination_data(self) -> dict[str, Any] | None:
        if not getattr(self, "page", None):
            return None
        return {
            "page": self.page.number,
            "per_page": self.page.paginator.per_page,
            "total": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "previous": self.get_previous_link(),
            "next": self.get_next_link(),
        }

    def apply_filters_to_queryset(
        self,
        queryset: QuerySet,
        raw_filter: dict[str, Any] | None = None,
        raw_exclude: dict[str, Any] | None = None,
        raw_order_by: str | None = None,
        search_value: str | None = None,
    ) -> QuerySet:
        filters = validate_filter_fields(raw_filter if raw_filter is not None else {}, self.allowed_filters)
        excludes = validate_filter_fields(raw_exclude if raw_exclude is not None else {}, self.allowed_excludes)
        order = validate_order_by_field(raw_order_by, self.allowed_order_by)
        queryset = queryset.filter(**filters).exclude(**excludes)
        if search_value and self.search:
            query = Q()
            for field in self.search:
                query |= Q(**{f"{field}__icontains": str(search_value).strip()})
            queryset = queryset.filter(query)
        return queryset.order_by(order)

    def render_list(self, queryset: QuerySet, request: Request) -> Response:
        paginated = self.required_pagination or "page" in request.query_params or "per_page" in request.query_params
        results = self.paginate_queryset(queryset, request, view=self) if paginated else queryset
        serializer = self.get_serializer_class("paginated" if paginated else "default")
        data = self.filter_response_data(serializer(results, many=True).data)
        return ApiResponse.success(data=data, pagination=self.get_pagination_data() if paginated else None)
