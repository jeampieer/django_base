"""Subconjunto genérico del manejador de excepciones del proyecto de origen."""

import logging
from typing import Any

from django.conf import settings
from django.core.exceptions import FieldError, ObjectDoesNotExist
from django.db import IntegrityError
from django.http import Http404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.api.filters import InvalidFilterFieldError
from core.api.responses import ApiResponse

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    if isinstance(exc, (Http404, ObjectDoesNotExist)):
        return ApiResponse.not_found()
    if isinstance(exc, (FieldError, InvalidFilterFieldError)):
        return ApiResponse.error("Filtros inválidos.", details=str(exc), error_type="invalid_filter")
    if isinstance(exc, IntegrityError):
        logger.exception("Error de integridad")
        return ApiResponse.error("Los datos incumplen una restricción de integridad.")
    response = drf_exception_handler(exc, context)
    if response is not None:
        details = response.data
        message = "Error de validación" if isinstance(exc, ValidationError) else str(getattr(exc, "detail", exc))
        return ApiResponse.error(
            message, code=response.status_code, error_type=type(exc).__name__,
            details=details, headers=dict(response.items()),
        )
    logger.exception("Error interno de la API")
    return ApiResponse.internal_error(details=str(exc) if settings.DEBUG else None)
