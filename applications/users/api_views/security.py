from uuid import UUID

from rest_framework.request import Request
from rest_framework.response import Response

from applications.users.api_views.user import UserDetailView
from applications.users.schemas.endpoints import events_schema, sessions_schema
from applications.users.selectors.security import security_events_for_user, sessions_for_user
from applications.users.serializers.security import SecurityEventSerializer, UserSessionSerializer
from core.api.responses import ApiResponse


class UserSessionsView(UserDetailView):
    policy_action = "read"
    http_method_names = ["get", "head", "options"]

    @sessions_schema
    def get(self, request: Request, pk: UUID) -> Response:
        target = self.get_object(pk)
        page = self.paginate_queryset(sessions_for_user(user=target), request, view=self)
        return ApiResponse.success(
            data=UserSessionSerializer(page, many=True).data, pagination=self.get_pagination_data(),
        )


class UserSecurityEventsView(UserDetailView):
    policy_action = "read"
    http_method_names = ["get", "head", "options"]

    @events_schema
    def get(self, request: Request, pk: UUID) -> Response:
        target = self.get_object(pk)
        page = self.paginate_queryset(security_events_for_user(user=target), request, view=self)
        return ApiResponse.success(
            data=SecurityEventSerializer(page, many=True).data, pagination=self.get_pagination_data(),
        )
