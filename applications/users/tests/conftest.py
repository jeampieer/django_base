from django.contrib.auth import get_user_model
import pytest

User = get_user_model()
# Credencial ficticia exclusiva de tests, sin relación con cuentas reales.
EXAMPLE_PASSWORD = "Fictional-Password-9!xO"


@pytest.fixture
def login_user(user_reader: User) -> User:
    user_reader.set_password(EXAMPLE_PASSWORD)
    user_reader.save(update_fields=["password"])
    return user_reader
