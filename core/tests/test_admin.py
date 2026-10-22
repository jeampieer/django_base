from types import SimpleNamespace
from typing import Any

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.test import RequestFactory
from django.utils import timezone
import pytest

from core.admin import BaseModelAdmin
from core.admin.base import execute_form

User = get_user_model()


def test_audit_fieldsets_are_copied_without_duplicates() -> None:
    model_admin = BaseModelAdmin(User, admin.site)
    original = [("Información", {"fields": (("username", "created"), "modified", "email")}),
                ("Auditoría", {"fields": ("created_by", "updated_by")})]
    result = model_admin.with_audit_fieldsets(original)
    assert result[0][1]["fields"] == [("username",), "email"]
    assert len(result) == 2 and result[-1][0] == "Auditoría"
    assert original[0][1]["fields"] == (("username", "created"), "modified", "email")
    request = RequestFactory().get("/")
    model_admin.readonly_fields = ("created", "username")
    assert model_admin.get_readonly_fields(request).count("created") == 1
    assert "id" in model_admin.get_readonly_fields(request)


def test_audit_formatters_escape_names_and_handle_missing_values() -> None:
    model_admin = BaseModelAdmin(User, admin.site)
    actor = SimpleNamespace(first_name="<script>", last_name="Example", email='"unsafe@example.test',
                            get_username=lambda: "fallback")
    obj = SimpleNamespace(created=timezone.now(), modified=timezone.now(), created_by=actor,
                          updated_by=None, is_active=True)
    assert "<script>" not in model_admin.format_created_by(obj)
    assert "&lt;script&gt;" in model_admin.format_created_by(obj)
    assert "&quot;" in model_admin.format_created_by(obj)
    assert model_admin.format_updated_by(obj) == "-"
    assert "Activo" in model_admin.format_is_active(obj)
    assert model_admin.format_created(obj) != "-" and model_admin.format_modified(obj) != "-"
    obj.created, obj.modified, obj.is_active = None, None, False
    assert model_admin.format_created(obj) == "-" and model_admin.format_modified(obj) == "-"
    assert "Inactivo" in model_admin.format_is_active(obj)
    actor.first_name, actor.last_name = "", ""
    assert "fallback" in model_admin.format_created_by(obj)


def test_hard_delete_hooks_are_disabled() -> None:
    model_admin = BaseModelAdmin(User, admin.site)
    request = RequestFactory().post("/")
    with pytest.raises(PermissionDenied):
        model_admin.delete_model(request, None)
    with pytest.raises(PermissionDenied):
        model_admin.delete_queryset(request, None)


def test_operation_converts_django_validation_to_native_errors() -> None:
    from django import forms

    class SampleForm(forms.Form):
        name = forms.CharField()

    def fail(data: Any) -> None:
        raise DjangoValidationError({"name": ["Invalid name"]})

    form = SampleForm({"name": "Example"})
    assert not execute_form(form, fail)
    assert form.errors["name"] == ["Invalid name"]
