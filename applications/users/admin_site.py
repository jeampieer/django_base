from typing import Any

from django.contrib import admin, messages
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.exceptions import PermissionDenied as ServicePermissionDenied

from applications.users.forms import AdminPasswordForm
from applications.users.models import User
from applications.users.permissions.rules import can_access_admin
from applications.users.services.change_password import ChangePasswordService
from applications.users.services.logout import LogoutService
from core.admin.base import execute_form, render_operation


class ServiceAdminSite(admin.AdminSite):
    site_header = "Administración del backend"
    site_title = "Administración"
    index_title = "Gestión interna"
    site_url = None

    def has_permission(self, request: HttpRequest) -> bool:
        return can_access_admin(request.user)

    def password_change(self, request: HttpRequest, extra_context: Any = None) -> HttpResponse:
        form = AdminPasswordForm(request.POST if request.method == "POST" else None, require_current=True)
        if request.method == "POST" and execute_form(form, lambda data: ChangePasswordService(
            actor=request.user, target=request.user,
        ).execute(new_password=data["new_password1"], current_password=data["current_password"])):
            logout(request)
            messages.success(request, "Contraseña actualizada. Inicie sesión nuevamente.")
            return redirect(reverse("admin:login"))
        return render_operation(request, site=self, form=form, title="Cambiar mi contraseña",
                                opts=User._meta, original=request.user)

    def logout(self, request: HttpRequest, extra_context: Any = None) -> HttpResponse:
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        try:
            LogoutService(user=request.user).execute()
        except ServicePermissionDenied as exc:
            raise PermissionDenied(str(exc.detail)) from exc
        return super().logout(request, extra_context)
