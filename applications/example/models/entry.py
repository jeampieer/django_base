from django.db import models

from core.models import BaseModel


class EntryStatusChoices(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    FINALIZED = "FINALIZED", "Finalizada"


class Entry(BaseModel):
    title = models.CharField("Título", max_length=150)
    label = models.ForeignKey(
        "example.Label", on_delete=models.PROTECT, related_name="entries", verbose_name="Etiqueta",
    )
    status = models.CharField(
        "Estado", max_length=12, choices=EntryStatusChoices.choices, default=EntryStatusChoices.DRAFT,
    )
    summary = models.CharField("Resumen", max_length=250, blank=True)
    finalized_at = models.DateTimeField("Finalizada el", null=True, blank=True, editable=False)

    class Meta(BaseModel.Meta):
        verbose_name = "Entrada"
        verbose_name_plural = "Entradas"
