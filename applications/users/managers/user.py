from typing import Any

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager

from core.auth.roles import default_role


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username: str, email: str, password: str | None = None, **extra_fields: Any) -> Any:
        if not username or not email:
            raise ValueError("username y email son obligatorios.")
        extra_fields.setdefault("role", default_role())
        if extra_fields["role"] not in settings.USER_ROLES:
            raise ValueError("El rol no está configurado.")
        user = self.model(username=username, email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, email: str, password: str | None = None, **extra_fields: Any) -> Any:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", settings.USER_SUPERUSER_ROLE)
        if extra_fields["is_staff"] is not True or extra_fields["is_superuser"] is not True:
            raise ValueError("Un superusuario requiere is_staff=True e is_superuser=True.")
        return self.create_user(username=username, email=email, password=password, **extra_fields)
