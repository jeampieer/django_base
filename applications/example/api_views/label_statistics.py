from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.example.models import Label
from applications.example.schemas.label_statistics import label_statistics_schema
from applications.example.selectors.label_statistics import labels_with_entry_counts
from applications.example.serializers.label_statistics import (
    LabelStatisticsInputSerializer,
    LabelStatisticsOutputSerializer,
)
from core.api.responses import ApiResponse
from core.auth.permissions import HasModelPolicy


class LabelStatisticsView(APIView):
    model = Label
    policy_action = "read"
    permission_classes = [HasModelPolicy]

    @label_statistics_schema
    def get(self, request: Request) -> Response:
        serializer = LabelStatisticsInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        result = labels_with_entry_counts(**serializer.validated_data)
        return ApiResponse.success(data=LabelStatisticsOutputSerializer(result, many=True).data)
