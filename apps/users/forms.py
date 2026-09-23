"""
Forms for the users app.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Row, Submit
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile information.
    """

    first_name = forms.CharField(
        label=_("First name"),
        max_length=150,
        required=False,
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=150,
        required=False,
    )

    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "default_currency",
            "language",
            "timezone",
            "measurement_unit",
            "country_code",
            "avatar",
        ]
        labels = {
            "full_name": _("Full name"),
            "default_currency": _("Default currency"),
            "language": _("Language"),
            "timezone": _("Timezone"),
            "measurement_unit": _("Measurement unit"),
            "country_code": _("Country"),
            "avatar": _("Avatar"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            Row(
                Field("first_name", css_class="form-control"),
                Field("last_name", css_class="form-control"),
                css_class="row g-3",
            ),
            Row(
                Field("full_name", css_class="form-control"),
                css_class="row g-3",
            ),
            Row(
                Field("default_currency", css_class="form-select"),
                Field("measurement_unit", css_class="form-select"),
                css_class="row g-3",
            ),
            Row(
                Field("language", css_class="form-control"),
                Field("timezone", css_class="form-control"),
                css_class="row g-3",
            ),
            Row(
                Field("country_code", css_class="form-control"),
                Field("avatar", css_class="form-control"),
                css_class="row g-3",
            ),
            Submit("submit", _("Save"), css_class="btn btn-primary mt-3"),
        )

        # Populate first_name and last_name from the user
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

    def save(self, commit=True):
        """Save the profile and update the user's first/last name."""
        profile = super().save(commit=False)
        
        # Update user's first and last name
        user = profile.user
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        
        if commit:
            user.save()
            profile.save()
        
        return profile


class AccountDeleteForm(forms.Form):
    """
    Form for account deletion confirmation.
    Requires the user to type their email to confirm.
    """

    confirmation_email = forms.EmailField(
        label=_("Type your email to confirm"),
        help_text=_("Type your email address to confirm account deletion."),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Field("confirmation_email", css_class="form-control"),
            Submit(
                "submit",
                _("Delete my account"),
                css_class="btn btn-danger mt-3",
            ),
        )

    def clean_confirmation_email(self):
        """Validate that the confirmation email matches the user's email."""
        email = self.cleaned_data.get("confirmation_email")
        if self.user and email != self.user.email:
            raise forms.ValidationError(
                _("The email does not match your account email.")
            )
        return email