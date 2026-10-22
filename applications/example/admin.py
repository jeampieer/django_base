from typing import Any

from django.contrib import admin, messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from applications.example.forms import FinalizeEntryForm
from applications.example.models import Entry, Label
from applications.example.services.finalize_entry import FinalizeEntryService
from core.admin import BaseModelAdmin
from core.admin.base import execute_form, render_operation


@admin.register(Label)
class LabelAdmin(BaseModelAdmin):
    list_display = ("name", "format_is_active", "format_created", "format_created_by")
    list_filter = ("is_active", "created")
    search_fields = ("name",)
    list_select_related = ("created_by", "updated_by")
    fieldsets = (("Información", {"fields": ("name", "is_active")}),)


@admin.register(Entry)
class EntryAdmin(BaseModelAdmin):
    list_display = ("title", "label", "status", "format_is_active", "format_created", "format_created_by")
    list_filter = ("status", "is_active", "label", "created")
    search_fields = ("title", "label__name")
    list_select_related = ("label", "created_by", "updated_by")
    readonly_fields = ("status", "summary", "finalized_at", "finalize_action")
    fieldsets = (
        ("Información", {"fields": ("title", "label", "is_active")}),
        ("Finalización", {"fields": ("status", "summary", "finalized_at", "finalize_action")}),
    )

    @admin.display(description="Operación")
    def finalize_action(self, obj: Entry) -> str:
        if obj._state.adding:
            return "Guarde la entrada antes de finalizarla."
        return format_html('<a href="{}">Finalizar entrada</a>', self.operation_url(obj, "finalize"))

    def get_urls(self) -> list[Any]:
        return [path("<path:object_id>/finalize/", self.admin_site.admin_view(self.finalize_view),
                     name="example_entry_finalize")] + super().get_urls()

    def finalize_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        entry = self.get_object(request, object_id)
        if entry is None:
            raise Http404
        form = FinalizeEntryForm(request.POST if request.method == "POST" else None)
        if request.method == "POST" and execute_form(form, lambda data: FinalizeEntryService(
            actor=request.user, entry=entry,
        ).execute(**data)):
            self.log_change(request, entry, "Entrada finalizada mediante service.")
            messages.success(request, "Entrada finalizada.")
            return redirect(reverse("admin:example_entry_change", args=[entry.pk]))
        return render_operation(request, site=self.admin_site, form=form, title="Finalizar entrada",
                                opts=self.opts, original=entry)
