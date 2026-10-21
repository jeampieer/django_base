"""Base extraída del proyecto de origen: UUID, timestamps y auditoría."""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel


class BaseModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField("Activo", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="%(class)s_created",
        verbose_name="Creado por",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="%(class)s_updated",
        verbose_name="Actualizado por",
    )

    class Meta:
        abstract = True
        ordering = ["-created"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        user = kwargs.pop("user", None)
        if self._state.adding and user:
            self.created_by = user
        if not self._state.adding and user:
            self.updated_by = user
        super().save(*args, **kwargs)

    def save_with_user(self, user: Any) -> None:
        self.save(user=user)

    def soft_delete(self, user: Any = None) -> None:
        self.is_active = False
        if user:
            self.updated_by = user
        self.save(update_fields=["is_active", "modified", "updated_by"])

    def restore(self, user: Any = None) -> None:
        self.is_active = True
        if user:
            self.updated_by = user
        self.save(update_fields=["is_active", "modified", "updated_by"])

    def __str__(self) -> str:
        return f"{self.__class__.__name__} #{self.pk}"
