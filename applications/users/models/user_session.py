import uuid

from django.conf import settings
from django.db import models


class SessionStatusChoices(models.TextChoices):
    SUCCESS = "SUCCESS", "Exitoso"
    FAILED = "FAILED", "Fallido"


class SessionFailureChoices(models.TextChoices):
    INVALID_PASSWORD = "INVALID_PASSWORD", "Contraseña incorrecta"
    USER_NOT_FOUND = "USER_NOT_FOUND", "Usuario inexistente"
    INACTIVE_ACCOUNT = "INACTIVE_ACCOUNT", "Cuenta inactiva"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED", "Cuenta bloqueada"
    INVALID_ROLE = "INVALID_ROLE", "Rol no configurado"


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sessions", verbose_name="Usuario",
    )
    attempted_username = models.CharField("Usuario intentado", max_length=150)
    status = models.CharField("Resultado", max_length=10, choices=SessionStatusChoices.choices)
    failure_reason = models.CharField("Motivo", max_length=30, choices=SessionFailureChoices.choices, blank=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.TextField("Agente de usuario", blank=True)
    login_at = models.DateTimeField("Fecha de intento", auto_now_add=True)
    logout_at = models.DateTimeField("Cierre de sesión", null=True, blank=True)

    class Meta:
        ordering = ["-login_at"]
        verbose_name = "Intento de autenticación"
        verbose_name_plural = "Intentos de autenticación"
