from __future__ import annotations

from django.db.models import QuerySet

from applications.example.models import Entry
from applications.example.schemas.crud import entry_detail_schema, entry_filter_schema, entry_list_schema
from applications.example.serializers.entry import EntryDetailSerializer, EntrySerializer
from core.api.views import CustomDetailView, CustomFilterView, CustomListView


class EntryQuerysetMixin:
    def get_queryset(self) -> QuerySet[Entry]:
        return super().get_queryset().select_related("label")


@entry_list_schema
class EntryListView(EntryQuerysetMixin, CustomListView):
    model = Entry
    serializer = EntrySerializer
    detail_serializer = EntryDetailSerializer
    allowed_filters = ("title", "status", "is_active")
    allowed_order_by = ("created", "title")
    required_pagination = True


@entry_detail_schema
class EntryDetailView(EntryQuerysetMixin, CustomDetailView):
    model = Entry
    serializer = EntrySerializer
    detail_serializer = EntryDetailSerializer


@entry_filter_schema
class EntryFilterView(EntryQuerysetMixin, CustomFilterView):
    model = Entry
    serializer = EntrySerializer
    detail_serializer = EntryDetailSerializer
    allowed_filters = ("title", "status", "is_active")
    allowed_order_by = ("created", "title")
    required_pagination = True
