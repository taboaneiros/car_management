"""
Forms for the fuel app.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Fieldset, Layout, Row, Submit
from django import forms
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import FuelType, Refueling


class RefuelingForm(forms.ModelForm):
    """
    Form for creating and updating refuelings.
    """

    class Meta:
        model = Refueling
        fields = [
            "vehicle",
            "occurred_at",
            "station_name",
            "odometer",
            "liters",
            "total_amount",
            "price_per_liter",
            "fuel_type",
            "is_full_tank",
            "is_partial",
            "missed_previous_fillup",
            "notes",
            "attachment",
        ]
        labels = {
            "vehicle": _("Vehicle"),
            "occurred_at": _("Date"),
            "station_name": _("Gas Station"),
            "odometer": _("Odometer (km)"),
            "liters": _("Liters"),
            "total_amount": _("Total Amount (R$)"),
            "price_per_liter": _("Price per Liter"),
            "fuel_type": _("Fuel Type"),
            "is_full_tank": _("Full Tank"),
            "is_partial": _("Partial Refueling"),
            "missed_previous_fillup": _("Missed Previous Fill-up"),
            "notes": _("Notes"),
            "attachment": _("Attachment"),
        }
        widgets = {
            "occurred_at": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
            "odometer": forms.NumberInput(attrs={"min": 0}),
            "liters": forms.NumberInput(attrs={"step": "0.001", "min": 0}),
            "total_amount": forms.NumberInput(
                attrs={"step": "0.01", "min": 0, "readonly": "readonly", "id": "id_total_amount"}
            ),
            "price_per_liter": forms.NumberInput(attrs={"step": "0.0001", "min": 0, "id": "id_price_per_liter"}),
        }

    def __init__(self, *args, vehicle=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle_param = vehicle
        self.user = user

        # Set default date to today
        if not self.instance.pk:
            self.initial["occurred_at"] = timezone.now().date()

        # Filter vehicles by user and set up the vehicle field
        if user:
            from apps.vehicles.models import Vehicle
            self.fields["vehicle"].queryset = Vehicle.objects.filter(
                owner_primary=user,
                is_active=True,
            )
            # If only one vehicle, pre-select it
            if self.fields["vehicle"].queryset.count() == 1:
                self.initial["vehicle"] = self.fields["vehicle"].queryset.first()

        # If vehicle is passed via URL, pre-select and hide the field
        if vehicle:
            self.initial["vehicle"] = vehicle
            self.fields["vehicle"].widget = forms.HiddenInput()

        # Filter fuel types by user, including system fuel types
        if user:
            self.fields["fuel_type"].queryset = FuelType.objects.filter(
                is_active=True,
            ).filter(
                models.Q(user=user) | models.Q(user__isnull=True),
            ).order_by("name")

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        
        # Build layout - include vehicle field only if not hidden
        if vehicle:
            # Vehicle is hidden, don't include in layout
            self.helper.layout = Layout(
                Fieldset(
                    _("Refueling Information"),
                    Row(
                        Field("occurred_at", css_class="form-control"),
                        Field("station_name", css_class="form-control"),
                        css_class="row g-3",
                    ),
                    Row(
                        Field("odometer", css_class="form-control"),
                        Field("fuel_type", css_class="form-select"),
                        css_class="row g-3",
                    ),
                ),
                Fieldset(
                    _("Fuel and Price"),
                    Row(
                        Field("liters", css_class="form-control"),
                        Field("total_amount", css_class="form-control"),
                        css_class="row g-3",
                    ),
                    Row(
                        Field("price_per_liter", css_class="form-control"),
                        css_class="col-12",
                    ),
                ),
                Fieldset(
                    _("Tank Status"),
                    Row(
                        Field("is_full_tank", css_class="form-check-input"),
                        Field("is_partial", css_class="form-check-input"),
                        Field("missed_previous_fillup", css_class="form-check-input"),
                        css_class="row g-3",
                    ),
                ),
                Fieldset(
                    _("Additional Information"),
                    Field("notes", css_class="form-control", rows=3),
                    Field("attachment", css_class="form-control"),
                ),
                Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
            )
        else:
            # Show vehicle selection field
            self.helper.layout = Layout(
                Fieldset(
                    _("Vehicle"),
                    Row(
                        Field("vehicle", css_class="form-select"),
                        css_class="row g-3",
                    ),
                ),
                Fieldset(
                    _("Refueling Information"),
                    Row(
                        Field("occurred_at", css_class="form-control"),
                        Field("station_name", css_class="form-control"),
                        css_class="row g-3",
                    ),
                    Row(
                        Field("odometer", css_class="form-control"),
                        Field("fuel_type", css_class="form-select"),
                        css_class="row g-3",
                    ),
                ),
                Fieldset(
                    _("Fuel and Price"),
                    Row(
                        Field("liters", css_class="form-control"),
                        Field("total_amount", css_class="form-control"),
                        css_class="row g-3",
                    ),
                    Row(
                        Field("price_per_liter", css_class="form-control"),
                        css_class="col-12",
                    ),
                ),
                Fieldset(
                    _("Tank Status"),
                    Row(
                        Field("is_full_tank", css_class="form-check-input"),
                        Field("is_partial", css_class="form-check-input"),
                        Field("missed_previous_fillup", css_class="form-check-input"),
                        css_class="row g-3",
                    ),
                ),
                Fieldset(
                    _("Additional Information"),
                    Field("notes", css_class="form-control", rows=3),
                    Field("attachment", css_class="form-control"),
                ),
                Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
            )

    def clean_odometer(self):
        """Validate odometer reading."""
        odometer = self.cleaned_data.get("odometer")
        if odometer < 0:
            raise forms.ValidationError(_("Odometer cannot be negative."))
        vehicle = self.cleaned_data.get("vehicle") or self.vehicle_param
        if vehicle and odometer < vehicle.initial_odometer:
            raise forms.ValidationError(
                _("Odometer cannot be less than the initial odometer (%(initial)s)."),
                code="invalid",
                params={"initial": vehicle.initial_odometer},
            )
        return odometer

    def clean_liters(self):
        """Validate liters."""
        liters = self.cleaned_data.get("liters")
        if liters <= 0:
            raise forms.ValidationError(_("Liters must be greater than zero."))
        return liters

    def clean_total_amount(self):
        """Validate total amount."""
        amount = self.cleaned_data.get("total_amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError(_("Total amount must be greater than zero."))
        return amount

    def clean(self):
        """
        Calculate total_amount or price_per_liter if one is missing.
        This ensures the backend always has consistent data.
        """
        cleaned_data = super().clean()
        liters = cleaned_data.get("liters")
        total_amount = cleaned_data.get("total_amount")
        price_per_liter = cleaned_data.get("price_per_liter")

        # Calculate total_amount from liters * price_per_liter
        if liters and price_per_liter and not total_amount:
            cleaned_data["total_amount"] = liters * price_per_liter

        # Calculate price_per_liter from total_amount / liters
        elif liters and total_amount and not price_per_liter:
            cleaned_data["price_per_liter"] = total_amount / liters

        # Validate that we have enough data
        if liters and not total_amount and not price_per_liter:
            raise forms.ValidationError(
                _("Please provide either the total amount or the price per liter.")
            )

        return cleaned_data


class FuelTypeForm(forms.ModelForm):
    """
    Form for creating fuel types.
    """

    class Meta:
        model = FuelType
        fields = ["name", "code"]
        labels = {
            "name": _("Name"),
            "code": _("Code"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Field("name", css_class="form-control"),
                Field("code", css_class="form-control"),
                css_class="row g-3",
            ),
            Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
        )