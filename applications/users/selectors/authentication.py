from dataclasses import dataclass
from uuid import UUID

from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from applications.users.models import User


@dataclass(frozen=True)
class RefreshContext:
    user: User
    token: RefreshToken


def refresh_context_get(*, refresh: str) -> RefreshContext:
    try:
        token = RefreshToken(refresh)
        user = User.objects.get(pk=UUID(str(token["user_id"])))
    except (TokenError, KeyError, ValueError, User.DoesNotExist) as exc:
        raise InvalidToken("Refresh inválido.") from exc
    return RefreshContext(user=user, token=token)
