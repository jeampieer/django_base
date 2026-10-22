from typing import Any

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from applications.users.models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "role")


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("username", "password", "email", "first_name", "last_name", "role", "is_active")


class AdminPasswordForm(forms.Form):
    current_password = forms.CharField(label="Contraseña actual", widget=forms.PasswordInput, strip=False)
    new_password1 = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput, strip=False)
    new_password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput, strip=False)

    def __init__(self, *args: Any, require_current: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not require_current:
            self.fields.pop("current_password")

    def clean(self) -> dict[str, Any]:
        data = super().clean()
        if data.get("new_password1") != data.get("new_password2"):
            self.add_error("new_password2", "Las contraseñas no coinciden.")
        return data
