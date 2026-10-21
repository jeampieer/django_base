from typing import Any
from uuid import UUID

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from applications.users.models import User
from applications.users.permissions.user import CanEditUser
from applications.users.schemas.endpoints import user_detail_schema, user_filter_schema, user_list_schema
from applications.users.serializers.actions import SetUserActiveOutputSerializer
from applications.users.serializers.user import (
    CreateUserInputSerializer, CreateUserOutputSerializer, UpdateUserInputSerializer, UpdateUserOutputSerializer,
    UserDetailSerializer, UserSerializer,
)
from applications.users.services.create_user import CreateUserService
from applications.users.services.set_user_active import SetUserActiveService
from applications.users.services.update_user import UpdateUserService
from core.api.responses import ApiResponse
from core.api.views import CustomDetailView, CustomFilterView, CustomListView
from core.auth.permissions import HasModelPolicy


@user_list_schema
class UserListView(CustomListView):
    model = User
    serializer = UserSerializer
    detail_serializer = UserDetailSerializer
    required_pagination = True
    allowed_filters = ("username", "email", "first_name", "last_name", "role", "is_active")
    allowed_order_by = ("created", "username", "first_name", "last_name")
    search = ("username", "email", "first_name", "last_name")

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = CreateUserInputSerializer(data=self.validate_request_data("create"))
        serializer.is_valid(raise_exception=True)
        user = CreateUserService(actor=request.user).execute(**serializer.validated_data)
        return ApiResponse.created(data=CreateUserOutputSerializer(user).data)


@user_detail_schema
class UserDetailView(CustomDetailView):
    model = User
    serializer = UserSerializer
    detail_serializer = UserDetailSerializer
    permission_classes = [IsAuthenticated, HasModelPolicy, CanEditUser]

    def put(self, request: Request, pk: UUID, *args: Any, **kwargs: Any) -> Response:
        target = self.get_object(pk)
        serializer = UpdateUserInputSerializer(data=self.validate_request_data("update"))
        serializer.is_valid(raise_exception=True)
        user = UpdateUserService(actor=request.user, target=target).execute(changes=serializer.validated_data)
        return ApiResponse.success(data=UpdateUserOutputSerializer(user).data)

    def delete(self, request: Request, pk: UUID, *args: Any, **kwargs: Any) -> Response:
        target = self.get_object(pk)
        self.check_delete_permission(obj=target)
        user = SetUserActiveService(actor=request.user, target=target).execute(is_active=False)
        return ApiResponse.success(data=SetUserActiveOutputSerializer(user).data)


@user_filter_schema
class UserFilterView(CustomFilterView):
    model = User
    serializer = UserSerializer
    detail_serializer = UserDetailSerializer
    required_pagination = True
    allowed_filters = UserListView.allowed_filters
    allowed_order_by = UserListView.allowed_order_by
    search = UserListView.search
