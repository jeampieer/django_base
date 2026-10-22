from dataclasses import dataclass

from django.db import transaction
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from applications.users.models import User
from applications.users.services.authenticate_user import AuthenticateUserService


@dataclass(frozen=True)
class LoginResult:
    access: str
    refresh: str
    user: User


class LoginService:
    def __init__(self, *, user: User | None) -> None:
        self.user = user

    def execute(self, *, attempted_username: str, password: str,
                ip_address: str | None = None, user_agent: str = "") -> LoginResult:
        # Compartir autenticación sin cambiar el commit de auditoría ni la emisión JWT original.
        with transaction.atomic():
            user = AuthenticateUserService(user=self.user)._authenticate(
                attempted_username=attempted_username, password=password, ip_address=ip_address, user_agent=user_agent,
            )
            if user is not None:
                refresh = RefreshToken.for_user(user)
                result = LoginResult(access=str(refresh.access_token), refresh=str(refresh), user=user)
        if user is None:
            raise AuthenticationFailed("Credenciales incorrectas o cuenta no disponible.")
        return result
