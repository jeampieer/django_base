"""Factory ApiResponse extraída, conservando el contrato JSON de origen."""

from datetime import datetime, timezone
from typing import Any

from rest_framework import status as http_status
from rest_framework.response import Response

VALID_HTTP_CODES = {value for value in vars(http_status).values() if isinstance(value, int)}


class ApiResponse:
    def __new__(
        cls,
        data: Any = None,
        message: str | None = None,
        success: bool = True,
        code: int = 200,
        error: dict[str, Any] | None = None,
        pagination: dict[str, Any] | None = None,
        deprecated: bool = False,
        replacement: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> Response:
        valid_code = code if code in VALID_HTTP_CODES else 500
        meta: dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat()}
        if pagination:
            meta["pagination"] = pagination
        if deprecated:
            meta["deprecated"] = True
            if replacement:
                meta["replacement"] = replacement
        payload = {
            "success": success,
            "status": "success" if success else "error",
            "message": message,
            "data": data if success else None,
            "meta": meta,
        }
        if error:
            payload["error"] = error
        return Response(payload, status=valid_code, headers=headers or {})

    @classmethod
    def success(cls, data: Any = None, message: str = "Operación exitosa", **kwargs: Any) -> Response:
        return cls(data=data, message=message, success=True, **kwargs)

    @classmethod
    def created(cls, data: Any = None, message: str = "Recurso creado exitosamente", **kwargs: Any) -> Response:
        return cls(data=data, message=message, code=201, **kwargs)

    @classmethod
    def no_content(cls, message: str = "Operación exitosa sin contenido", **kwargs: Any) -> Response:
        return cls(message=message, code=204, **kwargs)

    @classmethod
    def error(
        cls,
        message: str,
        code: int = 400,
        error_type: str = "business_logic_error",
        details: Any = None,
        **kwargs: Any,
    ) -> Response:
        error = {
            "code": code,
            "type": error_type,
            "message": message,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return cls(message=message, success=False, code=code, error=error, **kwargs)

    @classmethod
    def validation_error(cls, errors: Any, message: str = "Error de validación", **kwargs: Any) -> Response:
        return cls.error(message, code=422, error_type="validation_error", details=errors, **kwargs)

    @classmethod
    def not_found(cls, message: str = "Recurso no encontrado", **kwargs: Any) -> Response:
        return cls.error(message, code=404, error_type="not_found", **kwargs)

    @classmethod
    def unauthorized(cls, message: str = "No autenticado", **kwargs: Any) -> Response:
        return cls.error(message, code=401, error_type="authentication_error", **kwargs)

    @classmethod
    def forbidden(cls, message: str = "No tiene permisos para realizar esta acción", **kwargs: Any) -> Response:
        return cls.error(message, code=403, error_type="authorization_error", **kwargs)

    @classmethod
    def internal_error(cls, message: str = "Error interno del servidor", **kwargs: Any) -> Response:
        return cls.error(message, code=500, error_type="internal_error", **kwargs)
