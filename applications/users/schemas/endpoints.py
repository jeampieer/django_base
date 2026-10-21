from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers

from applications.users.serializers.actions import (
    ChangePasswordInputSerializer, ChangePasswordOutputSerializer,
    ChangeRoleInputSerializer, ChangeRoleOutputSerializer,
    SetUserActiveInputSerializer, SetUserActiveOutputSerializer,
)
from applications.users.serializers.authentication import (
    LoginInputSerializer, LoginOutputSerializer, LogoutInputSerializer, LogoutOutputSerializer,
    RefreshInputSerializer, RefreshOutputSerializer, VerifyInputSerializer, VerifyOutputSerializer,
)
from applications.users.serializers.security import SecurityEventSerializer, UserSessionSerializer
from applications.users.serializers.user import (
    CreateUserInputSerializer, CreateUserOutputSerializer, UpdateUserInputSerializer, UpdateUserOutputSerializer,
    UserDetailSerializer,
)
from core.api.openapi import response_schema

user_item = response_schema(name="UserResponse", data=UserDetailSerializer())
user_list = response_schema(name="UserListResponse", data=UserDetailSerializer(many=True))
state_response = response_schema(name="UserStateResponse", data=SetUserActiveOutputSerializer())
user_list_schema = extend_schema_view(
    get=extend_schema(operation_id="users_list", responses=user_list, tags=["Usuarios"]),
    post=extend_schema(operation_id="users_create", request=CreateUserInputSerializer,
                       responses={201: response_schema(name="UserCreatedResponse", data=CreateUserOutputSerializer())},
                       tags=["Usuarios"]),
)
update_response = response_schema(name="UserUpdatedResponse", data=UpdateUserOutputSerializer())
user_detail_schema = extend_schema_view(
    get=extend_schema(operation_id="users_retrieve", responses=user_item, tags=["Usuarios"]),
    put=extend_schema(operation_id="users_update", request=UpdateUserInputSerializer,
                      responses=update_response, tags=["Usuarios"]),
    patch=extend_schema(operation_id="users_partial_update", request=UpdateUserInputSerializer,
                        responses=update_response, tags=["Usuarios"]),
    delete=extend_schema(operation_id="users_delete", request=None, responses=state_response, tags=["Usuarios"]),
)
user_filter_schema = extend_schema_view(post=extend_schema(
    operation_id="users_filter", tags=["Usuarios"], responses=user_list,
    request=inline_serializer(name="UserFilters", fields={
        "filter": serializers.DictField(required=False), "exclude": serializers.DictField(required=False),
        "order_by": serializers.CharField(required=False), "q": serializers.CharField(required=False),
    }),
))
login_schema = extend_schema(
    operation_id="users_login", request=LoginInputSerializer,
    responses=response_schema(name="LoginResponse", data=LoginOutputSerializer()), tags=["Auth"],
)
refresh_schema = extend_schema(
    operation_id="users_refresh", request=RefreshInputSerializer,
    responses=response_schema(name="RefreshResponse", data=RefreshOutputSerializer()), tags=["Auth"],
)
verify_schema = extend_schema(
    operation_id="users_verify", request=VerifyInputSerializer,
    responses=response_schema(name="VerifyResponse", data=VerifyOutputSerializer()), tags=["Auth"],
)
logout_schema = extend_schema(
    operation_id="users_logout", request=LogoutInputSerializer,
    responses=response_schema(name="LogoutResponse", data=LogoutOutputSerializer()), tags=["Auth"],
)
current_user_schema = extend_schema(operation_id="users_me", responses=user_item, tags=["Auth"])
password_schema = extend_schema(
    request=ChangePasswordInputSerializer,
    responses=response_schema(name="PasswordChangedResponse", data=ChangePasswordOutputSerializer()), tags=["Usuarios"],
)
role_schema = extend_schema(
    operation_id="users_change_role", request=ChangeRoleInputSerializer,
    responses=response_schema(name="RoleChangedResponse", data=ChangeRoleOutputSerializer()), tags=["Usuarios"],
)
activate_schema = extend_schema(
    operation_id="users_activate", request=SetUserActiveInputSerializer, responses=state_response, tags=["Usuarios"],
)
deactivate_schema = extend_schema(
    operation_id="users_deactivate", request=SetUserActiveInputSerializer, responses=state_response, tags=["Usuarios"],
)
sessions_schema = extend_schema(
    operation_id="users_sessions", tags=["Usuarios"],
    responses=response_schema(name="UserSessionsResponse", data=UserSessionSerializer(many=True)),
)
events_schema = extend_schema(operation_id="users_security_events", tags=["Usuarios"], responses=response_schema(
    name="UserSecurityEventsResponse", data=SecurityEventSerializer(many=True),
))
