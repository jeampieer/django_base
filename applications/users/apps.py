from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "applications.users"
    verbose_name = "Usuarios"

    def ready(self) -> None:
        from core.auth.registry import policy_registry
        from .policies import UserPolicy

        policy_registry.register(UserPolicy)
