"""
Forms for the maintenance app.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Fieldset, Layout, Row, Submit
from django import forms
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Maintenance, ServiceType


class MaintenanceForm(forms.ModelForm):
    """Form for creating and editing maintenance records."""

    class Meta:
        model = Maintenance
        fields = [
            "vehicle",
            "service_type",
            "maintenance_type",
            "occurred_at",
            "odometer",
            "total_amount",
            "workshop_name",
            "description",
            "reminder",
            "notes",
            "attachment",
        ]
        labels = {
            "vehicle": _("Vehicle"),
            "service_type": _("Service Type"),
            "maintenance_type": _("Maintenance Type"),
            "occurred_at": _("Date"),
            "odometer": _("Odometer (km)"),
            "total_amount": _("Total Amount (R$)"),
            "workshop_name": _("Workshop / Mechanic"),
            "description": _("Description"),
            "reminder": _("Associated Reminder"),
            "notes": _("Notes"),
            "attachment": _("Invoice / Attachment"),
        }
        widgets = {
            "occurred_at": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
            "total_amount": forms.NumberInput(attrs={"step": "0.01", "min": 0}),
            "odometer": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, vehicle=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle_param = vehicle
        self.user = user

        if not self.instance.pk:
            self.initial["occurred_at"] = timezone.now().date()

        if user:
            from apps.vehicles.models import Vehicle
            self.fields["vehicle"].queryset = Vehicle.objects.filter(
                owner_primary=user,
                is_active=True,
            )
            if self.fields["vehicle"].queryset.count() == 1:
                self.initial["vehicle"] = self.fields["vehicle"].queryset.first()

            self.fields["service_type"].queryset = ServiceType.objects.filter(
                is_active=True,
            ).filter(
                models.Q(user=user) | models.Q(user__isnull=True),
            ).order_by("name")

            from apps.reminders.models import Reminder
            reminder_qs = Reminder.objects.filter(
                vehicle__owner_primary=user,
                status="pending",
            )
            if vehicle:
                reminder_qs = reminder_qs.filter(vehicle=vehicle)
            self.fields["reminder"].queryset = reminder_qs.order_by("due_date", "title")

        if vehicle:
            self.initial["vehicle"] = vehicle
            self.fields["vehicle"].widget = forms.HiddenInput()

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"

        vehicle_row = []
        if not vehicle:
            vehicle_row = [
                Fieldset(
                    _("Vehicle"),
                    Row(
                        Field("vehicle", css_class="form-select"),
                        css_class="row g-3",
                    ),
                )
            ]

        self.helper.layout = Layout(
            *vehicle_row,
            Fieldset(
                _("Maintenance Info"),
                Row(
                    Field("service_type", css_class="form-select"),
                    Field("maintenance_type", css_class="form-select"),
                    css_class="row g-3",
                ),
                Row(
                    Field("occurred_at", css_class="form-control"),
                    Field("odometer", css_class="form-control"),
                    Field("total_amount", css_class="form-control"),
                    css_class="row g-3",
                ),
            ),
            Fieldset(
                _("Details & Workshop"),
                Row(
                    Field("workshop_name", css_class="form-control"),
                    Field("description", css_class="form-control"),
                    css_class="row g-3",
                ),
                Row(
                    Field("reminder", css_class="form-select"),
                    css_class="row g-3",
                ),
            ),
            Fieldset(
                _("Attachments & Notes"),
                Field("notes", css_class="form-control", rows=3),
                Field("attachment", css_class="form-control"),
            ),
            Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
        )

    def clean_total_amount(self):
        amount = self.cleaned_data.get("total_amount")
        if amount is not None and amount < 0:
            raise forms.ValidationError(_("Amount cannot be negative."))
        return amount

    def clean_odometer(self):
        odometer = self.cleaned_data.get("odometer")
        if odometer is not None and odometer < 0:
            raise forms.ValidationError(_("Odometer cannot be negative."))
        return odometer


class ServiceTypeForm(forms.ModelForm):
    """Form for custom service types."""

    class Meta:
        model = ServiceType
        fields = [
            "name",
            "description",
            "default_interval_km",
            "default_interval_months",
        ]
        labels = {
            "name": _("Name"),
            "description": _("Description"),
            "default_interval_km": _("Default Interval (km)"),
            "default_interval_months": _("Default Interval (months)"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Field("name", css_class="form-control"),
                css_class="col-12",
            ),
            Row(
                Field("default_interval_km", css_class="form-control"),
                Field("default_interval_months", css_class="form-control"),
                css_class="row g-3",
            ),
            Field("description", css_class="form-control", rows=2),
            Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
        )

