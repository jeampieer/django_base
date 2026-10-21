"""Checks de infraestructura extraídos del original y adaptados a ApiResponse."""

import logging
from typing import Any

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.responses import ApiResponse

logger = logging.getLogger(__name__)


class PingView(APIView):
    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    @extend_schema(responses=OpenApiTypes.OBJECT, summary="Comprobar proceso")
    def get(self, request: Request) -> Response:
        return ApiResponse.success(data={"status": "ok", "message": "pong"})


class HealthCheckView(PingView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT}, summary="Comprobar dependencias")
    def get(self, request: Request) -> Response:
        checks = {"database": "ok", "cache": "ok"}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            logger.exception("Fallo de base de datos en health check")
            checks["database"] = "error"
        try:
            cache.set("health_check_test", "ok", timeout=10)
            if cache.get("health_check_test") != "ok":
                checks["cache"] = "error"
            cache.delete("health_check_test")
        except Exception:
            logger.exception("Fallo de cache en health check")
            checks["cache"] = "error"
        if "error" in checks.values():
            return ApiResponse.error("Dependencias no disponibles.", code=503, details=checks)
        return ApiResponse.success(data={"status": "healthy", "checks": checks})
