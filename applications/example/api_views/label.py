from applications.example.models import Label
from applications.example.schemas.crud import label_detail_schema, label_filter_schema, label_list_schema
from applications.example.serializers.label import LabelDetailSerializer, LabelSerializer
from core.api.views import CustomDetailView, CustomFilterView, CustomListView


@label_list_schema
class LabelListView(CustomListView):
    model = Label
    serializer = LabelSerializer
    detail_serializer = LabelDetailSerializer
    allowed_filters = ("name", "is_active")
    allowed_order_by = ("created", "name")
    search = ("name",)
    required_pagination = True


@label_detail_schema
class LabelDetailView(CustomDetailView):
    model = Label
    serializer = LabelSerializer
    detail_serializer = LabelDetailSerializer


@label_filter_schema
class LabelFilterView(CustomFilterView):
    model = Label
    serializer = LabelSerializer
    detail_serializer = LabelDetailSerializer
    allowed_filters = ("name", "is_active")
    allowed_order_by = ("created", "name")
    required_pagination = True
