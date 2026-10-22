from django.contrib.admin.apps import SimpleAdminConfig


class TemplateAdminConfig(SimpleAdminConfig):
    default_site = "applications.users.admin_site.ServiceAdminSite"

    def ready(self) -> None:
        super().ready()
        # Registro explícito: no añadir editores de grupos, permisos ni tokens de terceros.
        from applications.users import admin as users_admin  # noqa: F401
        from applications.example import admin as example_admin  # noqa: F401
