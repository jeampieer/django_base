from typing import Any

from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers

from applications.example.serializers.entry import EntryDetailSerializer, EntrySerializer
from applications.example.serializers.label import LabelDetailSerializer, LabelSerializer
from core.api.openapi import response_schema


def crud_schemas(*, name: str, write: Any, read: Any) -> tuple[Any, Any, Any]:
    item = response_schema(name=f"{name}Response", data=read())
    listing = response_schema(name=f"{name}ListResponse", data=read(many=True))
    deleted = response_schema(name=f"{name}DeleteResponse", data=serializers.JSONField(allow_null=True))
    filters = inline_serializer(name=f"{name}Filters", fields={
        "filter": serializers.DictField(required=False),
        "exclude": serializers.DictField(required=False),
        "order_by": serializers.CharField(required=False),
        "q": serializers.CharField(required=False),
    })
    return (
        extend_schema_view(
            get=extend_schema(operation_id=f"{name.lower()}_list", responses=listing, tags=[name]),
            post=extend_schema(
                operation_id=f"{name.lower()}_create", request=write, responses={201: item}, tags=[name],
            ),
        ),
        extend_schema_view(
            get=extend_schema(operation_id=f"{name.lower()}_retrieve", responses=item, tags=[name]),
            put=extend_schema(operation_id=f"{name.lower()}_update", request=write, responses=item, tags=[name]),
            patch=extend_schema(
                operation_id=f"{name.lower()}_partial_update", request=write, responses=item, tags=[name],
            ),
            delete=extend_schema(operation_id=f"{name.lower()}_delete", responses=deleted, tags=[name]),
        ),
        extend_schema_view(post=extend_schema(
            operation_id=f"{name.lower()}_filter", request=filters, responses=listing, tags=[name],
        )),
    )


label_list_schema, label_detail_schema, label_filter_schema = crud_schemas(
    name="Label", write=LabelSerializer, read=LabelDetailSerializer,
)
entry_list_schema, entry_detail_schema, entry_filter_schema = crud_schemas(
    name="Entry", write=EntrySerializer, read=EntryDetailSerializer,
)
