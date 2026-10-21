from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import close_old_connections, connection, connections
from model_bakery import baker
import pytest
from rest_framework.exceptions import ValidationError

from applications.example.models import Entry, EntryStatusChoices, Label
from applications.example.services.finalize_entry import FinalizeEntryService

User = get_user_model()


@pytest.mark.django_db(transaction=True)
def test_only_one_concurrent_finalization_succeeds() -> None:
    if connection.vendor != "postgresql":
        pytest.skip("El bloqueo de filas se verifica con PostgreSQL, como en CI.")
    actor = baker.make(User, role=settings.USER_SUPERUSER_ROLE, is_active=True)
    entry = baker.make(Entry, label=baker.make(Label), created_by=actor)
    barrier = Barrier(2)

    def finalize(summary: str) -> str:
        close_old_connections()
        try:
            local_actor = User.objects.get(pk=actor.pk)
            local_entry = Entry.objects.get(pk=entry.pk)
            barrier.wait(timeout=10)
            try:
                FinalizeEntryService(actor=local_actor, entry=local_entry).execute(summary=summary)
                return "finalized"
            except ValidationError:
                return "rejected"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(finalize, ["Primera", "Segunda"]))
    assert sorted(result) == ["finalized", "rejected"]
    entry.refresh_from_db()
    assert entry.status == EntryStatusChoices.FINALIZED
