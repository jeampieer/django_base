"""Django Admin nativo con auditoría, basado en el patrón de Iperc."""

from typing import Any

from django import forms
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import PermissionDenied as ServicePermissionDenied, ValidationError


def add_form_errors(form: forms.BaseForm, detail: Any) -> None:
    """Traduce errores de services a campos nativos sin mostrar datos internos de BD."""
    if isinstance(detail, dict):
        for field, errors in detail.items():
            form.add_error(field if field in form.fields else None, forms.ValidationError(errors))
    else:
        form.add_error(None, forms.ValidationError(detail))


def execute_form(form: forms.BaseForm, execute: Any) -> bool:
    if not form.is_valid():
        return False
    try:
        execute(form.cleaned_data)
    except ServicePermissionDenied as exc:
        raise PermissionDenied(str(exc.detail)) from exc
    except ValidationError as exc:
        add_form_errors(form, exc.detail)
        return False
    except DjangoValidationError as exc:
        add_form_errors(form, exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return False
    except IntegrityError:
        form.add_error(None, "Los valores duplican un registro o incumplen una relación.")
        return False
    except ObjectDoesNotExist as exc:
        raise Http404("El registro ya no existe.") from exc
    return True


def render_operation(request: HttpRequest, *, site: admin.AdminSite, form: forms.Form,
                     title: str, opts: Any, original: Any) -> HttpResponse:
    """Reutiliza change_form.html, sus widgets, fieldsets y protección CSRF."""
    if not site.has_permission(request):
        raise PermissionDenied
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])
    from django.contrib.admin.helpers import AdminForm
    request.current_app = site.name
    return TemplateResponse(request, "admin/change_form.html", {
        **site.each_context(request), "title": title, "opts": opts, "original": original,
        "adminform": AdminForm(form, [(None, {"fields": list(form.fields)})], {}),
        "media": form.media, "errors": form.errors, "inline_admin_formsets": [],
        "add": False, "change": True, "is_popup": False, "save_as": False,
        "has_view_permission": True, "has_change_permission": True,
        "has_add_permission": False, "has_delete_permission": False,
        "has_editable_inline_admin_formsets": False, "show_save_and_continue": False,
        "show_save_and_add_another": False, "show_delete": False,
        "app_label": opts.app_label,
    })


class BaseModelAdmin(admin.ModelAdmin):
    audit_readonly_fields = ("id", "created", "modified", "created_by", "updated_by")
    date_hierarchy = "created"
    actions = None
    list_per_page = 50
    save_as = False

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*super().get_readonly_fields(request, obj), *self.audit_readonly_fields)))

    def with_audit_fieldsets(self, fieldsets: Any) -> list[Any]:
        cleaned = []
        for title, options in fieldsets:
            fields = []
            for field in options.get("fields", ()):
                if isinstance(field, (tuple, list)):
                    remaining = tuple(item for item in field if item not in self.audit_readonly_fields)
                    if remaining:
                        fields.append(remaining)
                elif field not in self.audit_readonly_fields:
                    fields.append(field)
            if fields:
                cleaned.append((title, {**options, "fields": fields}))
        cleaned.append(("Auditoría", {
            "classes": ("collapse",), "fields": ("id", ("created", "modified"), ("created_by", "updated_by")),
            "description": "Información registrada automáticamente; no editable.",
        }))
        return cleaned

    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> list[Any]:
        return self.with_audit_fieldsets(super().get_fieldsets(request, obj))

    def get_form(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        form_class = super().get_form(request, obj, **kwargs)
        errors = getattr(request, "_admin_service_errors", None)
        if errors is None:
            return form_class

        class ServiceErrorForm(form_class):
            def _post_clean(self) -> None:
                super()._post_clean()
                add_form_errors(self, errors)

        return ServiceErrorForm

    @method_decorator(csrf_protect)
    def changeform_view(self, request: HttpRequest, object_id: str | None = None,
                        form_url: str = "", extra_context: Any = None) -> HttpResponse:
        # Django 5.2.8: conservar el formulario nativo, omitiendo únicamente su atomic exterior.
        # Las transacciones de negocio son de los services; los errores se renderizan sin reintentar escrituras.
        if request.method not in ("GET", "POST"):
            return HttpResponseNotAllowed(["GET", "POST"])
        try:
            return self._changeform_view(request, object_id, form_url, extra_context)
        except ServicePermissionDenied as exc:
            raise PermissionDenied(str(exc.detail)) from exc
        except ObjectDoesNotExist as exc:
            raise Http404 from exc
        except (ValidationError, DjangoValidationError) as exc:
            request._admin_service_errors = (
                exc.detail if isinstance(exc, ValidationError) else
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            )
        except IntegrityError:
            request._admin_service_errors = "Los valores duplican un registro o incumplen una relación."
        try:
            return self._changeform_view(request, object_id, form_url, extra_context)
        finally:
            del request._admin_service_errors

    def save_model(self, request: HttpRequest, obj: Any, form: Any, change: bool) -> None:
        obj.save_with_user(request.user)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def delete_model(self, request: HttpRequest, obj: Any) -> None:
        raise PermissionDenied("Utilice la desactivación; no se permite eliminación física.")

    def delete_queryset(self, request: HttpRequest, queryset: Any) -> None:
        raise PermissionDenied("No se permite eliminación física ni acciones masivas.")

    @admin.display(description="Creado", ordering="created")
    def format_created(self, obj: Any) -> str:
        return timezone.localtime(obj.created).strftime("%d/%m/%Y %H:%M") if obj.created else "-"

    @admin.display(description="Modificado", ordering="modified")
    def format_modified(self, obj: Any) -> str:
        return timezone.localtime(obj.modified).strftime("%d/%m/%Y %H:%M") if obj.modified else "-"

    @staticmethod
    def _format_actor(actor: Any) -> str:
        if actor is None:
            return "-"
        name = " ".join(filter(None, (getattr(actor, "first_name", ""), getattr(actor, "last_name", ""))))
        return format_html('<span title="{}">{}</span>', actor.email, name or actor.get_username())

    @admin.display(description="Creado por", ordering="created_by")
    def format_created_by(self, obj: Any) -> str:
        return self._format_actor(obj.created_by)

    @admin.display(description="Actualizado por", ordering="updated_by")
    def format_updated_by(self, obj: Any) -> str:
        return self._format_actor(obj.updated_by)

    @admin.display(description="Estado", ordering="is_active")
    def format_is_active(self, obj: Any) -> str:
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>',
                           "green" if obj.is_active else "red", "✓ Activo" if obj.is_active else "✗ Inactivo")

    def operation_url(self, obj: Any, action: str) -> str:
        return reverse(f"admin:{self.opts.app_label}_{self.opts.model_name}_{action}", args=[obj.pk])


class ReadOnlyModelAdmin(admin.ModelAdmin):
    actions = None
    list_per_page = 50

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        return tuple(field.name for field in self.model._meta.fields)
