"""Adaptador Celery: valida el mensaje, resuelve entidades y llama al service."""

from uuid import UUID
import logging

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from applications.example.selectors.entry import actor_get, entry_get
from applications.example.services.finalize_entry import FinalizeEntryService

logger = logging.getLogger(__name__)


@shared_task
def finalize_entry(*, entry_id: str, actor_id: str, summary: str) -> str | None:
    if not isinstance(entry_id, str):
        raise ValueError("entry_id debe ser un UUID en texto.")
    pk = UUID(entry_id)
    if not isinstance(actor_id, str):
        raise ValueError("actor_id debe ser un UUID en texto.")
    actor_pk = UUID(actor_id)
    if not isinstance(summary, str):
        raise ValueError("summary debe ser texto.")
    try:
        entry = entry_get(pk=pk)
        actor = actor_get(pk=actor_pk)
        result = FinalizeEntryService(actor=actor, entry=entry).execute(summary=summary)
    except ObjectDoesNotExist:
        logger.info("Finalización omitida: entrada o usuario inexistente. entry=%s actor=%s", pk, actor_pk)
        return None
    return str(result.pk)
