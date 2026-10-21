from uuid import UUID

from applications.users.models import User


def user_get(*, pk: UUID) -> User:
    return User.objects.get(pk=pk)


def user_find_by_username(*, username: str) -> User | None:
    return User.objects.filter(username=username).first()
