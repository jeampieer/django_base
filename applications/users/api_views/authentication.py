from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.users.schemas.endpoints import (
    current_user_schema, login_schema, logout_schema, refresh_schema, verify_schema,
)
from applications.users.selectors.authentication import refresh_context_get
from applications.users.selectors.user import user_find_by_username
from applications.users.serializers.authentication import (
    LoginInputSerializer, LoginOutputSerializer, LogoutInputSerializer, LogoutOutputSerializer,
    RefreshInputSerializer, RefreshOutputSerializer, VerifyInputSerializer, VerifyOutputSerializer,
)
from applications.users.serializers.user import UserDetailSerializer
from applications.users.services.login import LoginService
from applications.users.services.logout import LogoutService
from applications.users.services.refresh_access_token import RefreshAccessTokenService
from applications.users.services.verify_token import VerifyTokenService
from core.api.responses import ApiResponse


class PublicTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="api"'


class LoginView(PublicTokenView):
    @login_schema
    def post(self, request: Request) -> Response:
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = user_find_by_username(username=data["username"])
        result = LoginService(user=user).execute(
            attempted_username=data["username"], password=data["password"],
            ip_address=request.META.get("REMOTE_ADDR"), user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
        )
        return ApiResponse.success(data=LoginOutputSerializer(result).data)


class RefreshView(PublicTokenView):

    @refresh_schema
    def post(self, request: Request) -> Response:
        serializer = RefreshInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        context = refresh_context_get(**serializer.validated_data)
        result = RefreshAccessTokenService(user=context.user).execute(refresh=context.token)
        return ApiResponse.success(data=RefreshOutputSerializer(result).data)


class VerifyView(PublicTokenView):

    @verify_schema
    def post(self, request: Request) -> Response:
        serializer = VerifyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = VerifyTokenService().execute(**serializer.validated_data)
        return ApiResponse.success(data=VerifyOutputSerializer(result).data)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @current_user_schema
    def get(self, request: Request) -> Response:
        return ApiResponse.success(data=UserDetailSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @logout_schema
    def post(self, request: Request) -> Response:
        serializer = LogoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LogoutService(user=request.user).execute()
        result = {"detail": "Refresh de todas las sesiones revocados."}
        return ApiResponse.success(data=LogoutOutputSerializer(result).data)
