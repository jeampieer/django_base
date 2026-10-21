from unittest.mock import patch

from django.contrib.auth import get_user_model
from model_bakery import baker
import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from applications.example.models import Entry, EntryStatusChoices, Label
from applications.example.services.finalize_entry import FinalizeEntryService

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_service_works_without_http(user_admin: User) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    result = FinalizeEntryService(actor=user_admin, entry=entry).execute(summary="  Listo  ")
    entry.refresh_from_db()
    assert entry.status == EntryStatusChoices.FINALIZED
    assert entry.summary == "Listo"
    assert result.updated_by == user_admin


@pytest.mark.parametrize("summary", ["", " ", "x" * 251])
def test_invalid_summary_leaves_draft(user_admin: User, summary: str) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    with pytest.raises(ValidationError):
        FinalizeEntryService(actor=user_admin, entry=entry).execute(summary=summary)
    entry.refresh_from_db()
    assert entry.status == EntryStatusChoices.DRAFT


def test_inactive_label_is_rejected(user_admin: User) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label, is_active=False))
    with pytest.raises(ValidationError):
        FinalizeEntryService(actor=user_admin, entry=entry).execute(summary="Listo")


def test_stale_entity_is_reloaded(user_admin: User) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    Entry.objects.filter(pk=entry.pk).update(status=EntryStatusChoices.FINALIZED)
    with pytest.raises(ValidationError):
        FinalizeEntryService(actor=user_admin, entry=entry).execute(summary="Listo")


def test_authorization_is_also_enforced_without_http(user_admin: User, user_reader: User) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    with pytest.raises(PermissionDenied):
        FinalizeEntryService(actor=user_reader, entry=entry).execute(summary="Listo")


def test_service_rolls_back_a_write_on_failure(user_admin: User) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    original_save = Entry.save

    def fail_after_save(instance: Entry, *args: object, **kwargs: object) -> None:
        original_save(instance, *args, **kwargs)
        raise RuntimeError("Fallo después de escribir")

    with patch.object(Entry, "save", fail_after_save), pytest.raises(RuntimeError):
        FinalizeEntryService(actor=user_admin, entry=entry).execute(summary="Listo")
    entry.refresh_from_db()
    assert entry.status == EntryStatusChoices.DRAFT
    assert entry.finalized_at is None
