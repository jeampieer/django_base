from uuid import UUID

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from applications.users.api_views.user import UserDetailView
from applications.users.permissions.user import CanManageUser
from applications.users.schemas.endpoints import activate_schema, deactivate_schema, password_schema, role_schema
from applications.users.serializers.actions import (
    ChangePasswordInputSerializer, ChangePasswordOutputSerializer,
    ChangeRoleInputSerializer, ChangeRoleOutputSerializer,
    SetUserActiveInputSerializer, SetUserActiveOutputSerializer,
)
from applications.users.services.change_password import ChangePasswordService
from applications.users.services.change_role import ChangeRoleService
from applications.users.services.set_user_active import SetUserActiveService
from core.api.responses import ApiResponse
from core.auth.permissions import HasModelPolicy


class ChangePasswordView(UserDetailView):
    policy_action = "update"
    http_method_names = ["post", "options"]

    @password_schema
    def post(self, request: Request, pk: UUID | None = None) -> Response:
        target = self.get_object(pk) if pk else request.user
        self.check_object_permissions(request, target)
        serializer = ChangePasswordInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = ChangePasswordService(actor=request.user, target=target).execute(**serializer.validated_data)
        return ApiResponse.success(data=ChangePasswordOutputSerializer(user).data)


class ChangeRoleView(UserDetailView):
    policy_action = "update"
    http_method_names = ["post", "options"]
    permission_classes = [IsAuthenticated, HasModelPolicy, CanManageUser]

    @role_schema
    def post(self, request: Request, pk: UUID) -> Response:
        target = self.get_object(pk)
        serializer = ChangeRoleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = ChangeRoleService(actor=request.user, target=target).execute(**serializer.validated_data)
        return ApiResponse.success(data=ChangeRoleOutputSerializer(user).data)


class UserStateView(UserDetailView):
    policy_action = "delete"
    http_method_names = ["post", "options"]
    permission_classes = [IsAuthenticated, HasModelPolicy, CanManageUser]
    target_active: bool

    def post(self, request: Request, pk: UUID) -> Response:
        target = self.get_object(pk)
        serializer = SetUserActiveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = SetUserActiveService(actor=request.user, target=target).execute(is_active=self.target_active)
        return ApiResponse.success(data=SetUserActiveOutputSerializer(user).data)


class ActivateUserView(UserStateView):
    target_active = True

    @activate_schema
    def post(self, request: Request, pk: UUID) -> Response:
        return super().post(request, pk)


class DeactivateUserView(UserStateView):
    target_active = False

    @deactivate_schema
    def post(self, request: Request, pk: UUID) -> Response:
        return super().post(request, pk)


class ChangeOwnPasswordView(ChangePasswordView):
    @extend_schema(operation_id="users_change_own_password")
    def post(self, request: Request) -> Response:
        return super().post(request)
