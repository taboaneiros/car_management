"""
Forms for the vehicles app.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Fieldset, Layout, Row, Submit
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Vehicle


class VehicleForm(forms.ModelForm):
    """
    Form for creating and updating vehicles.
    """

    class Meta:
        model = Vehicle
        fields = [
            "name",
            "brand",
            "model",
            "version",
            "year",
            "plate",
            "color",
            "vehicle_type",
            "fuel_control_type",
            "initial_odometer",
            "notes",
            "photo",
        ]
        labels = {
            "name": _("Name"),
            "brand": _("Brand"),
            "model": _("Model"),
            "version": _("Version"),
            "year": _("Year"),
            "plate": _("License Plate"),
            "color": _("Color"),
            "vehicle_type": _("Vehicle Type"),
            "fuel_control_type": _("Fuel Control Type"),
            "initial_odometer": _("Initial Odometer (km)"),
            "notes": _("Notes"),
            "photo": _("Photo"),
        }
        widgets = {
            "year": forms.NumberInput(attrs={"min": 1900, "max": 2100}),
            "initial_odometer": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            Fieldset(
                _("Vehicle Identification"),
                Row(
                    Field("name", css_class="form-control"),
                    Field("brand", css_class="form-control"),
                    css_class="row g-3",
                ),
                Row(
                    Field("model", css_class="form-control"),
                    Field("version", css_class="form-control"),
                    css_class="row g-3",
                ),
                Row(
                    Field("year", css_class="form-control"),
                    Field("plate", css_class="form-control"),
                    css_class="row g-3",
                ),
                Row(
                    Field("color", css_class="form-control"),
                    Field("vehicle_type", css_class="form-select"),
                    css_class="row g-3",
                ),
            ),
            Fieldset(
                _("Fuel and Odometer"),
                Row(
                    Field("fuel_control_type", css_class="form-select"),
                    Field("initial_odometer", css_class="form-control"),
                    css_class="row g-3",
                ),
            ),
            Fieldset(
                _("Additional Information"),
                Field("notes", css_class="form-control", rows=3),
                Field("photo", css_class="form-control"),
            ),
            Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
        )

    def clean_year(self):
        """Validate the year field."""
        year = self.cleaned_data.get("year")
        if year and year < 1900:
            raise forms.ValidationError(_("Year must be 1900 or later."))
        return year

    def clean_initial_odometer(self):
        """Validate the initial odometer field."""
        odometer = self.cleaned_data.get("initial_odometer")
        if odometer < 0:
            raise forms.ValidationError(_("Odometer cannot be negative."))
        return odometer