"""
Forms for the trips app.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Field, Fieldset, Layout, Row, Submit
from django import forms
from django.utils import timezone

from apps.vehicles.models import Vehicle

from .models import Trip, TripPurpose


class TripForm(forms.ModelForm):
    """Form for creating and updating trips/routes."""

    class Meta:
        model = Trip
        fields = [
            "vehicle",
            "origin",
            "destination",
            "purpose",
            "started_at",
            "ended_at",
            "start_odometer",
            "end_odometer",
            "distance",
            "rate_per_km",
            "total_cost",
            "driver_name",
            "freight_amount",
            "notes",
        ]
        widgets = {
            "started_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "ended_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "start_odometer": forms.NumberInput(attrs={"min": 0, "class": "form-control"}),
            "end_odometer": forms.NumberInput(attrs={"min": 0, "class": "form-control"}),
            "distance": forms.NumberInput(attrs={"step": "0.1", "min": 0, "class": "form-control"}),
            "rate_per_km": forms.NumberInput(attrs={"step": "0.001", "min": 0, "class": "form-control"}),
            "total_cost": forms.NumberInput(attrs={"step": "0.01", "min": 0, "class": "form-control"}),
            "freight_amount": forms.NumberInput(attrs={"step": "0.01", "min": 0, "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, user=None, vehicle=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user:
            self.fields["vehicle"].queryset = Vehicle.objects.filter(
                owner_primary=user, is_active=True
            )

        if vehicle:
            self.fields["vehicle"].initial = vehicle
            if not self.instance.pk and vehicle.current_odometer_cache:
                self.fields["start_odometer"].initial = vehicle.current_odometer_cache
        elif not self.instance.pk and "vehicle" in self.fields and self.fields["vehicle"].queryset.exists():
            first_v = self.fields["vehicle"].queryset.first()
            if first_v and first_v.current_odometer_cache:
                self.fields["start_odometer"].initial = first_v.current_odometer_cache

        if not self.instance.pk and not self.initial.get("started_at"):
            self.initial["started_at"] = timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M")

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("vehicle", css_class="col-md-6 mb-3"),
                Column("purpose", css_class="col-md-6 mb-3"),
            ),
            Row(
                Column("origin", css_class="col-md-6 mb-3"),
                Column("destination", css_class="col-md-6 mb-3"),
            ),
            Row(
                Column("started_at", css_class="col-md-6 mb-3"),
                Column("ended_at", css_class="col-md-6 mb-3"),
            ),
            Row(
                Column("start_odometer", css_class="col-md-4 mb-3"),
                Column("end_odometer", css_class="col-md-4 mb-3"),
                Column("distance", css_class="col-md-4 mb-3"),
            ),
            Row(
                Column("rate_per_km", css_class="col-md-4 mb-3"),
                Column("total_cost", css_class="col-md-4 mb-3"),
                Column("freight_amount", css_class="col-md-4 mb-3"),
            ),
            Row(
                Column("driver_name", css_class="col-md-12 mb-3"),
            ),
            Row(
                Column("notes", css_class="col-md-12 mb-3"),
            ),
        )

