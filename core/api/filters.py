"""Filtros del core original; la lista vacía ahora deniega todos los campos."""

from collections.abc import Mapping, Sequence
from typing import Any


class InvalidFilterFieldError(ValueError):
    """Un campo o la estructura de filtrado no está permitido."""


COMMON_LOOKUPS = {
    "exact", "iexact", "contains", "icontains", "in", "gt", "gte", "lt", "lte",
    "startswith", "istartswith", "endswith", "iendswith", "range", "date", "year",
    "month", "day", "isnull", "regex", "iregex",
}


def get_base_filter_field(field: str) -> str:
    parts = field.split("__")
    return "__".join(parts[:-1]) if len(parts) > 1 and parts[-1] in COMMON_LOOKUPS else field


def validate_filter_fields(
    raw_filter: Mapping[str, Any], allowed_fields: Sequence[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw_filter, Mapping):
        raise InvalidFilterFieldError("Los filtros deben ser un objeto JSON.")
    invalid = [key for key in raw_filter if get_base_filter_field(key) not in (allowed_fields or ())]
    if invalid:
        raise InvalidFilterFieldError(f"Campos no permitidos: {', '.join(invalid)}")
    return dict(raw_filter)


def validate_order_by_field(
    raw_field: str | None,
    allowed_fields: Sequence[str] | None = None,
    default: str = "-created",
) -> str:
    if raw_field is not None and not isinstance(raw_field, str):
        raise InvalidFilterFieldError("order_by debe ser texto.")
    if not raw_field:
        return default
    return raw_field if raw_field.lstrip("-") in (allowed_fields or ()) else default
