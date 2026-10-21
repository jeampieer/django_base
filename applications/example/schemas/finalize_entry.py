from drf_spectacular.utils import extend_schema

from applications.example.serializers.finalize_entry import FinalizeEntryInputSerializer, FinalizeEntryOutputSerializer
from core.api.openapi import response_schema

finalize_entry_schema = extend_schema(
    summary="Finalizar una entrada propia en borrador",
    request=FinalizeEntryInputSerializer,
    responses=response_schema(name="FinalizeEntryResponse", data=FinalizeEntryOutputSerializer()),
    tags=["Entry"],
)
