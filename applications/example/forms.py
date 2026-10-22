from django import forms


class FinalizeEntryForm(forms.Form):
    summary = forms.CharField(label="Resumen", max_length=250, widget=forms.Textarea)
