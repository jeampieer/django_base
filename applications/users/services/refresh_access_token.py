from django.conf import settings
from django.db import transaction
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from applications.users.models import User


class RefreshAccessTokenService:
    def __init__(self, *, user: User) -> None:
        self.user = user

    @transaction.atomic
    def execute(self, *, refresh: RefreshToken) -> dict[str, str]:
        user = User.objects.select_for_update().get(pk=self.user.pk)
        if not user.is_active or user.role not in settings.USER_ROLES or str(user.pk) != str(refresh["user_id"]):
            raise InvalidToken("Refresh inválido.")
        try:
            # Revalida tras adquirir el mismo bloqueo que utiliza logout.
            refresh.verify()
        except TokenError as exc:
            raise InvalidToken("Refresh inválido.") from exc
        return {"access": str(refresh.access_token)}
