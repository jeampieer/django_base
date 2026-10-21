"""Policies declarativas y presets extraídos, sin roles del dominio de origen."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.db.models import Q
from django.conf import settings

AUDIT_FIELDS = ("id", "created_by", "updated_by", "created", "modified")


def unrestricted_query(user: Any) -> Q:
    return Q()


@dataclass
class CreatePolicy:
    allowed_fields: list[str] | str = field(default_factory=list)
    auto_fields: dict[str, Callable[[Any], Any]] = field(default_factory=dict)


@dataclass
class ReadPolicy:
    fields: list[str] | str = "__all__"
    query_filter: Callable[[Any], Q] = unrestricted_query


@dataclass
class UpdatePolicy:
    allowed_fields: list[str] | str = field(default_factory=list)
    readonly_fields: list[str] | str = field(default_factory=list)


class AdminAccess:
    create = CreatePolicy(allowed_fields="__all__")
    read = ReadPolicy()
    update = UpdatePolicy(allowed_fields="__all__", readonly_fields=list(AUDIT_FIELDS))
    delete = True


class ReadOnlyAccess:
    create = CreatePolicy()
    read = ReadPolicy()
    update = UpdatePolicy(readonly_fields="__all__")
    delete = False


class NoAccess(ReadOnlyAccess):
    read = ReadPolicy(fields=[])


class BasePolicy:
    model_label: str
    capability: str = ""
    authenticated_access: type = NoAccess
    privileged_access: type = NoAccess
    superuser_access: type = AdminAccess

    @classmethod
    def to_role_dict(cls, role: str, *, superuser: bool = False) -> dict[str, Any]:
        definition = settings.USER_ROLES.get(role)
        role_class = NoAccess
        if superuser:
            role_class = cls.superuser_access
        elif definition is not None:
            role_class = (
                cls.privileged_access if cls.capability in definition["permissions"] else cls.authenticated_access
            )
        create = getattr(role_class, "create", CreatePolicy())
        read = getattr(role_class, "read", ReadPolicy(fields=[]))
        update = getattr(role_class, "update", UpdatePolicy())
        return {
            "create": {"allowed_fields": create.allowed_fields, "auto_fields": create.auto_fields},
            "read": {"fields": read.fields, "query_filter": read.query_filter},
            "update": {"allowed_fields": update.allowed_fields, "readonly_fields": update.readonly_fields},
            "delete": getattr(role_class, "delete", False),
        }
