"""Forma documental de ApiResponse; no participa en la ejecución HTTP."""

from typing import Any

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


def response_schema(*, name: str, data: Any) -> serializers.Serializer:
    return inline_serializer(name=name, fields={
        "success": serializers.BooleanField(),
        "status": serializers.CharField(),
        "message": serializers.CharField(allow_null=True),
        "data": data,
        "meta": serializers.DictField(),
    })
