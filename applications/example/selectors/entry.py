from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser

from applications.example.models import Entry


def entry_get(*, pk: UUID) -> Entry:
    return Entry.objects.select_related("label").get(pk=pk)


def actor_get(*, pk: UUID) -> AbstractBaseUser:
    return get_user_model().objects.get(pk=pk)
