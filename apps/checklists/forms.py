"""
Forms for the checklists app.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Field, Layout, Row
from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.vehicles.models import Vehicle

from .models import ChecklistInspection, ChecklistTemplate, ItemStatus


class ChecklistInspectionForm(forms.ModelForm):
    """Form to initiate or edit an inspection."""

    class Meta:
        model = ChecklistInspection
        fields = ["vehicle", "template", "title", "odometer", "checked_at", "notes"]
        widgets = {
            "checked_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "odometer": forms.NumberInput(attrs={"min": 0, "class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, user=None, vehicle=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user:
            self.fields["vehicle"].queryset = Vehicle.objects.filter(
                owner_primary=user, is_active=True
            )
            self.fields["template"].queryset = ChecklistTemplate.objects.filter(
                Q(user=user) | Q(is_system=True),
                is_active=True,
            )

        if vehicle:
            self.fields["vehicle"].initial = vehicle
            if not self.instance.pk and vehicle.current_odometer_cache:
                self.fields["odometer"].initial = vehicle.current_odometer_cache
        elif not self.instance.pk and "vehicle" in self.fields and self.fields["vehicle"].queryset.exists():
            first_v = self.fields["vehicle"].queryset.first()
            if first_v and first_v.current_odometer_cache:
                self.fields["odometer"].initial = first_v.current_odometer_cache

        if not self.instance.pk and not self.initial.get("checked_at"):
            self.initial["checked_at"] = timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M")

        if not self.instance.pk and not self.initial.get("title"):
            self.initial["title"] = "Inspeção Veicular"

        if not self.instance.pk and "template" in self.fields and not self.initial.get("template"):
            first_t = self.fields["template"].queryset.first()
            if first_t:
                self.initial["template"] = first_t

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("vehicle", css_class="col-md-6 mb-3"),
                Column("template", css_class="col-md-6 mb-3"),
            ),
            Row(
                Column("title", css_class="col-md-6 mb-3"),
                Column("odometer", css_class="col-md-3 mb-3"),
                Column("checked_at", css_class="col-md-3 mb-3"),
            ),
            Row(
                Column("notes", css_class="col-md-12 mb-3"),
            ),
        )

