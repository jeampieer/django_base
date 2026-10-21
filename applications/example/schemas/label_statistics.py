from drf_spectacular.utils import extend_schema

from applications.example.serializers.label_statistics import (
    LabelStatisticsInputSerializer,
    LabelStatisticsOutputSerializer,
)
from core.api.openapi import response_schema

label_statistics_schema = extend_schema(
    summary="Contar entradas activas por etiqueta",
    parameters=[LabelStatisticsInputSerializer],
    responses=response_schema(name="LabelStatisticsResponse", data=LabelStatisticsOutputSerializer(many=True)),
    tags=["Label"],
)
