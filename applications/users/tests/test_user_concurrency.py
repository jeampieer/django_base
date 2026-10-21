from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.conf import settings
from django.db import close_old_connections, connection, connections
from model_bakery import baker
import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from applications.users.models import User
from applications.users.services.set_user_active import SetUserActiveService


@pytest.mark.django_db(transaction=True)
def test_concurrent_cross_deactivation_preserves_an_active_superuser() -> None:
    if connection.vendor != "postgresql":
        pytest.skip("La concurrencia real se verifica con PostgreSQL.")
    first, second = baker.make(User, role=settings.USER_SUPERUSER_ROLE, is_superuser=True, _quantity=2)
    barrier = Barrier(2)

    def deactivate_pair(pair: tuple[User, User]) -> str:
        close_old_connections()
        try:
            actor, target = pair
            barrier.wait(timeout=10)
            try:
                SetUserActiveService(actor=actor, target=target).execute(is_active=False)
                return "deactivated"
            except (PermissionDenied, ValidationError):
                return "denied"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(deactivate_pair, [(first, second), (second, first)]))
    assert sorted(results) == ["deactivated", "denied"]
    assert User.objects.filter(is_superuser=True, is_active=True).count() == 1
