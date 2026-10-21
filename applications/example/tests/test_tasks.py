from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from model_bakery import baker
import pytest

from applications.example.models import Entry, EntryStatusChoices, Label
from applications.example.tasks import finalize_entry

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_task_resolves_entities_and_calls_service(user_admin: User) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    with patch("applications.example.tasks.FinalizeEntryService") as service:
        service.return_value.execute.return_value = entry
        result = finalize_entry.run(entry_id=str(entry.pk), actor_id=str(user_admin.pk), summary="Listo")
    service.assert_called_once_with(actor=user_admin, entry=entry)
    service.return_value.execute.assert_called_once_with(summary="Listo")
    assert result == str(entry.pk)


def test_eager_task_runs_real_service(user_admin: User) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    result = finalize_entry.delay(entry_id=str(entry.pk), actor_id=str(user_admin.pk), summary="Listo")
    assert result.get() == str(entry.pk)
    entry.refresh_from_db()
    assert entry.status == EntryStatusChoices.FINALIZED


@pytest.mark.parametrize("entry_id,actor_id,summary", [
    ("invalid", 1, "Listo"), (str(uuid4()), 0, "Listo"), (str(uuid4()), True, "Listo"),
    (str(uuid4()), 1, 123), (123, 1, "Listo"),
    (str(uuid4()), str(uuid4()), 123),
])
def test_task_rejects_bad_message_before_lookups(entry_id: object, actor_id: object, summary: object) -> None:
    with patch("applications.example.tasks.entry_get") as selector, pytest.raises((ValueError, TypeError)):
        finalize_entry.run(entry_id=entry_id, actor_id=actor_id, summary=summary)
    selector.assert_not_called()


def test_task_logs_missing_entry_and_exits(caplog: pytest.LogCaptureFixture, user_admin: User) -> None:
    with caplog.at_level("INFO"), patch("applications.example.tasks.FinalizeEntryService") as service:
        assert finalize_entry.run(entry_id=str(uuid4()), actor_id=str(user_admin.pk), summary="Listo") is None
    service.assert_not_called()
    assert "inexistente" in caplog.text


def test_task_logs_missing_actor_and_exits(user_admin: User, caplog: pytest.LogCaptureFixture) -> None:
    entry = baker.make(Entry, created_by=user_admin, label=baker.make(Label))
    with caplog.at_level("INFO"):
        assert finalize_entry.run(entry_id=str(entry.pk), actor_id=str(uuid4()), summary="Listo") is None
    entry.refresh_from_db()
    assert entry.status == EntryStatusChoices.DRAFT
    assert "inexistente" in caplog.text
