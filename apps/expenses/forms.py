"""
Forms for the expenses app.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Fieldset, Layout, Row, Submit
from django import forms
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import CategoryKind, Expense, ExpenseCategory


class ExpenseForm(forms.ModelForm):
    """
    Form for creating and updating expenses.
    """

    class Meta:
        model = Expense
        fields = [
            "vehicle",
            "category",
            "occurred_at",
            "amount",
            "description",
            "odometer",
            "vendor_name",
            "is_recurring",
            "notes",
            "attachment",
        ]
        labels = {
            "vehicle": _("Vehicle"),
            "category": _("Category"),
            "occurred_at": _("Date"),
            "amount": _("Amount (R$)"),
            "description": _("Description"),
            "odometer": _("Odometer (km)"),
            "vendor_name": _("Vendor"),
            "is_recurring": _("Recurring"),
            "notes": _("Notes"),
            "attachment": _("Attachment"),
        }
        widgets = {
            "occurred_at": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": 0}),
            "odometer": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, vehicle=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle_param = vehicle
        self.user = user

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

        if user:
            self.fields["category"].queryset = ExpenseCategory.objects.filter(
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
                    _("Expense Information"),
                    Row(
                        Field("category", css_class="form-select"),
                        Field("occurred_at", css_class="form-control"),
                        css_class="row g-3",
                    ),
                    Row(
                        Field("amount", css_class="form-control"),
                        Field("odometer", css_class="form-control"),
                        css_class="row g-3",
                    ),
                ),
                Fieldset(
                    _("Details"),
                    Row(
                        Field("description", css_class="form-control"),
                        Field("vendor_name", css_class="form-control"),
                        css_class="row g-3",
                    ),
                    Row(
                        Field("is_recurring", css_class="form-check-input"),
                        css_class="col-12",
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
                    _("Expense Information"),
                    Row(
                        Field("category", css_class="form-select"),
                        Field("occurred_at", css_class="form-control"),
                        css_class="row g-3",
                    ),
                    Row(
                        Field("amount", css_class="form-control"),
                        Field("odometer", css_class="form-control"),
                        css_class="row g-3",
                    ),
                ),
                Fieldset(
                    _("Details"),
                    Row(
                        Field("description", css_class="form-control"),
                        Field("vendor_name", css_class="form-control"),
                        css_class="row g-3",
                    ),
                    Row(
                        Field("is_recurring", css_class="form-check-input"),
                        css_class="col-12",
                    ),
                ),
                Fieldset(
                    _("Additional Information"),
                    Field("notes", css_class="form-control", rows=3),
                    Field("attachment", css_class="form-control"),
                ),
                Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
            )

    def clean_amount(self):
        """Validate amount."""
        amount = self.cleaned_data.get("amount")
        if amount <= 0:
            raise forms.ValidationError(_("Amount must be greater than zero."))
        return amount


class ExpenseCategoryForm(forms.ModelForm):
    """
    Form for creating expense categories.
    """

    class Meta:
        model = ExpenseCategory
        fields = ["name", "kind"]
        labels = {
            "name": _("Name"),
            "kind": _("Kind"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Field("name", css_class="form-control"),
                Field("kind", css_class="form-select"),
                css_class="row g-3",
            ),
            Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
        )

    def save(self, commit=True):
        """Auto-generate slug from name."""
        instance = super().save(commit=False)
        instance.slug = slugify(instance.name)
        if commit:
            instance.save()
        return instance