from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from applications.example.models import Entry, EntryStatusChoices, Label
from core.auth.roles import has_capability


class FinalizeEntryService:
    """Finaliza una entrada propia y activa asociada a una etiqueta activa."""

    def __init__(self, *, actor: AbstractBaseUser, entry: Entry) -> None:
        self.actor = actor
        self.entry = entry

    @transaction.atomic
    def execute(self, *, summary: str) -> Entry:
        # Relee y bloquea: no confía en el estado observado antes de la transacción.
        actor = get_user_model().objects.select_for_update().get(pk=self.actor.pk)
        entry = Entry.objects.select_for_update().get(pk=self.entry.pk)
        label = Label.objects.select_for_update().get(pk=entry.label_id)
        if not has_capability(actor, "example.write") or entry.created_by_id != actor.pk:
            raise PermissionDenied("Solo el autor con rol administrador puede finalizar la entrada.")
        if not entry.is_active or entry.status != EntryStatusChoices.DRAFT:
            raise ValidationError("La entrada debe estar activa y en borrador.")
        if not label.is_active:
            raise ValidationError("La etiqueta debe estar activa.")
        if not summary.strip() or len(summary) > 250:
            raise ValidationError({"summary": "Se requiere un resumen de hasta 250 caracteres."})
        entry.status = EntryStatusChoices.FINALIZED
        entry.summary = summary.strip()
        entry.finalized_at = timezone.now()
        entry.updated_by = actor
        entry.save(update_fields=["status", "summary", "finalized_at", "updated_by", "modified"])
        return entry
