import uuid

from django.conf import settings
from django.db import models


class SecurityEventActionChoices(models.TextChoices):
    USER_CREATED = "USER_CREATED", "Usuario creado"
    PROFILE_UPDATED = "PROFILE_UPDATED", "Perfil actualizado"
    PASSWORD_CHANGED = "PASSWORD_CHANGED", "Contraseña cambiada"
    ROLE_CHANGED = "ROLE_CHANGED", "Rol cambiado"
    USER_ACTIVATED = "USER_ACTIVATED", "Usuario activado"
    USER_DEACTIVATED = "USER_DEACTIVATED", "Usuario desactivado"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED", "Cuenta bloqueada"
    LOGOUT = "LOGOUT", "Sesiones cerradas"


class SecurityEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField("Acción", max_length=30, choices=SecurityEventActionChoices.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="security_events_as_actor", verbose_name="Actor",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="security_events_as_target", verbose_name="Usuario afectado",
    )
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    extra = models.JSONField("Contexto", default=dict)
    created = models.DateTimeField("Fecha", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = "Evento de seguridad"
        verbose_name_plural = "Eventos de seguridad"
