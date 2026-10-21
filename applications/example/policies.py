from core.auth.policy import AdminAccess, BasePolicy, ReadOnlyAccess


class LabelPolicy(BasePolicy):
    model_label = "example.Label"
    capability = "example.write"
    privileged_access = AdminAccess
    authenticated_access = ReadOnlyAccess


class EntryPolicy(BasePolicy):
    model_label = "example.Entry"
    capability = "example.write"
    privileged_access = AdminAccess
    authenticated_access = ReadOnlyAccess
