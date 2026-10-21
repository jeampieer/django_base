from uuid import UUID

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.example.models import Entry
from applications.example.permissions.entry import CanFinalizeEntry
from applications.example.schemas.finalize_entry import finalize_entry_schema
from applications.example.serializers.finalize_entry import FinalizeEntryInputSerializer, FinalizeEntryOutputSerializer
from applications.example.services.finalize_entry import FinalizeEntryService
from core.api.responses import ApiResponse
from core.auth.permissions import HasModelPolicy


class FinalizeEntryView(APIView):
    model = Entry
    policy_action = "update"
    permission_classes = [IsAuthenticated, HasModelPolicy, CanFinalizeEntry]

    @finalize_entry_schema
    def post(self, request: Request, pk: UUID) -> Response:
        serializer = FinalizeEntryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = get_object_or_404(Entry, pk=pk)
        self.check_object_permissions(request, entry)
        result = FinalizeEntryService(actor=request.user, entry=entry).execute(**serializer.validated_data)
        return ApiResponse.success(data=FinalizeEntryOutputSerializer(result).data)
