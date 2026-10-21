from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken


class VerifyTokenService:
    def execute(self, *, token: str) -> dict[str, bool]:
        try:
            parsed = UntypedToken(token)
            if parsed.get("token_type") == "refresh":
                RefreshToken(token)
        except TokenError as exc:
            raise InvalidToken("Token inválido.") from exc
        return {"valid": True}
