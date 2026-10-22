from typing import Any

from django.contrib import admin, messages
from django.contrib.auth import logout
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import path, reverse

from applications.users.forms import AdminPasswordForm, AdminUserChangeForm, AdminUserCreationForm
from applications.users.models import SecurityEvent, User, UserSession
from applications.users.services.change_password import ChangePasswordService
from applications.users.services.create_user import CreateUserService
from applications.users.services.update_user_from_admin import UpdateUserFromAdminService
from core.admin import BaseModelAdmin, ReadOnlyModelAdmin
from core.admin.base import execute_form, render_operation


@admin.register(User)
class UserAdmin(BaseModelAdmin):
    form = AdminUserChangeForm
    list_display = ("username", "email", "first_name", "last_name", "role", "format_is_active", "format_created")
    list_filter = ("role", "is_active", "is_superuser", "created")
    search_fields = ("username", "email", "first_name", "last_name")
    readonly_fields = ("is_staff", "is_superuser", "last_login", "last_password_change",
                       "failed_login_attempts", "locked_until")
    fieldsets = (
        ("Acceso", {"fields": ("username", "password")}),
        ("Información personal", {"fields": ("email", "first_name", "last_name")}),
        ("Rol y estado", {"fields": ("role", "is_active")}),
        ("Seguridad", {"classes": ("collapse",), "fields": (
            "is_staff", "is_superuser", "last_login", "last_password_change", "failed_login_attempts", "locked_until",
        )}),
    )
    add_fieldsets = (
        ("Acceso", {"fields": ("username", "password1", "password2")}),
        ("Información personal", {"fields": ("email", "first_name", "last_name", "role")}),
    )

    def get_fieldsets(self, request: HttpRequest, obj: User | None = None) -> list[Any]:
        if obj is None:
            return self.with_audit_fieldsets(self.add_fieldsets)
        return super().get_fieldsets(request, obj)

    def get_form(self, request: HttpRequest, obj: User | None = None, **kwargs: Any) -> Any:
        kwargs["form"] = AdminUserCreationForm if obj is None else AdminUserChangeForm
        return super().get_form(request, obj, **kwargs)

    def save_form(self, request: HttpRequest, form: Any, change: bool) -> User:
        # El service es el único que hashea y guarda; evitar UserCreationForm.save incluso con commit=False.
        return form.instance

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: bool) -> None:
        # No hay inlines ni M2M editables; las escrituras ya fueron completadas por el service.
        pass

    def save_model(self, request: HttpRequest, obj: User, form: Any, change: bool) -> None:
        data = form.cleaned_data
        if change:
            allowed = {"username", "email", "first_name", "last_name", "role", "is_active"}
            saved = UpdateUserFromAdminService(actor=request.user, target=obj).execute(
                changes={field: data[field] for field in form.changed_data if field in allowed},
            )
        else:
            saved = CreateUserService(actor=request.user).execute(
                **{field: data[field] for field in ("username", "email", "first_name", "last_name", "role")},
                password=data["password1"],
            )
        # El service puede devolver una instancia recién creada o releída bajo bloqueo.
        for field in obj._meta.concrete_fields:
            setattr(obj, field.attname, getattr(saved, field.attname))
        obj._state.adding, obj._state.db = False, saved._state.db

    def get_urls(self) -> list[Any]:
        return [path("<path:object_id>/password/", self.admin_site.admin_view(self.password_view),
                     name="users_user_password")] + super().get_urls()

    def password_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        target = self.get_object(request, object_id)
        if target is None:
            raise Http404
        form = AdminPasswordForm(
            request.POST if request.method == "POST" else None, require_current=target.pk == request.user.pk,
        )
        if request.method == "POST" and execute_form(form, lambda data: ChangePasswordService(
            actor=request.user, target=target,
        ).execute(new_password=data["new_password1"], current_password=data.get("current_password"))):
            self.log_change(request, target, "Contraseña cambiada mediante service.")
            messages.success(request, "Contraseña actualizada.")
            if target.pk == request.user.pk:
                logout(request)
                return redirect(reverse("admin:login"))
            return redirect(reverse("admin:users_user_change", args=[target.pk]))
        return render_operation(request, site=self.admin_site, form=form, title="Cambiar contraseña",
                                opts=self.opts, original=target)


@admin.register(UserSession)
class UserSessionAdmin(ReadOnlyModelAdmin):
    list_display = ("attempted_username", "status", "failure_reason", "user", "ip_address", "login_at")
    list_filter = ("status", "failure_reason", "login_at")
    search_fields = ("attempted_username", "user__username", "ip_address")
    list_select_related = ("user",)
    date_hierarchy = "login_at"


@admin.register(SecurityEvent)
class SecurityEventAdmin(ReadOnlyModelAdmin):
    list_display = ("action", "actor", "target_user", "created")
    list_filter = ("action", "created")
    search_fields = ("actor__username", "target_user__username")
    list_select_related = ("actor", "target_user")
    date_hierarchy = "created"
