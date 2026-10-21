from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from applications.users.managers.user import UserManager
from core.auth.roles import default_role, role_choices
from core.models import BaseModel


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    username = models.CharField(
        "Usuario de acceso", max_length=150, unique=True, validators=[UnicodeUsernameValidator()],
    )
    email = models.EmailField("Correo electrónico", unique=True)
    first_name = models.CharField("Nombres", max_length=150)
    last_name = models.CharField("Apellidos", max_length=150)
    role = models.CharField("Rol", max_length=64, choices=role_choices, default=default_role)
    is_staff = models.BooleanField("Acceso administrativo Django", default=False)
    last_password_change = models.DateTimeField("Último cambio de contraseña", null=True, blank=True, editable=False)
    failed_login_attempts = models.PositiveIntegerField("Intentos fallidos", default=0, editable=False)
    locked_until = models.DateTimeField("Bloqueado hasta", null=True, blank=True, editable=False)

    objects = UserManager()
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    class Meta(BaseModel.Meta):
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self) -> str:
        return self.username
