from django.db import models

from core.models import BaseModel


class Label(BaseModel):
    name = models.CharField("Nombre", max_length=100, unique=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Etiqueta"
        verbose_name_plural = "Etiquetas"
