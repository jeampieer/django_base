from applications.users.permissions.rules import visible_users_filter
from core.auth.policy import BasePolicy, CreatePolicy, ReadPolicy, UpdatePolicy

PROFILE_FIELDS = [
    "id", "username", "email", "first_name", "last_name", "role", "is_active",
    "created", "modified", "created_by", "updated_by", "last_login", "last_password_change",
]
EDIT_FIELDS = ["username", "email", "first_name", "last_name"]


class MemberAccess:
    create = CreatePolicy()
    read = ReadPolicy(fields=PROFILE_FIELDS, query_filter=visible_users_filter)
    update = UpdatePolicy(allowed_fields=["email", "first_name", "last_name"])
    delete = False


class ManagerAccess(MemberAccess):
    create = CreatePolicy(allowed_fields=[*EDIT_FIELDS, "password", "role"])
    update = UpdatePolicy(allowed_fields=EDIT_FIELDS)
    delete = True


class UserPolicy(BasePolicy):
    model_label = "users.User"
    capability = "users.manage"
    authenticated_access = MemberAccess
    privileged_access = ManagerAccess
    superuser_access = ManagerAccess
