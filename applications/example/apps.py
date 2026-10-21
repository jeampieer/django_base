from django.apps import AppConfig


class ExampleConfig(AppConfig):
    name = "applications.example"

    def ready(self) -> None:
        from core.auth.registry import policy_registry
        from .policies import EntryPolicy, LabelPolicy

        policy_registry.register(LabelPolicy)
        policy_registry.register(EntryPolicy)
