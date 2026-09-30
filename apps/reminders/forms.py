"""
Forms for the reminders app.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Fieldset, Layout, Row, Submit
from django import forms
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Reminder, ReminderStatus, ReminderType


class ReminderForm(forms.ModelForm):
    """Form for creating and editing vehicle reminders."""

    class Meta:
        model = Reminder
        fields = [
            "vehicle",
            "title",
            "reminder_type",
            "service_type",
            "due_date",
            "due_odometer",
            "alert_days_before",
            "alert_odometer_before",
            "is_recurring",
            "recurrence_interval_months",
            "recurrence_interval_km",
            "notify_by_email",
            "notes",
        ]
        labels = {
            "vehicle": _("Veículo"),
            "title": _("Título / Descrição"),
            "reminder_type": _("Tipo de Lembrete"),
            "service_type": _("Tipo de Serviço"),
            "due_date": _("Data Limite"),
            "due_odometer": _("Odômetro Limite (km)"),
            "alert_days_before": _("Avisar com antecedência (dias)"),
            "alert_odometer_before": _("Avisar com antecedência (km)"),
            "is_recurring": _("Repetir este lembrete periodicamente"),
            "recurrence_interval_months": _("Repetir a cada (meses)"),
            "recurrence_interval_km": _("Repetir a cada (km)"),
            "notify_by_email": _("Enviar notificação por e-mail"),
            "notes": _("Observações"),
        }
        help_texts = {
            "due_date": _("Data de vencimento do lembrete"),
            "due_odometer": _("Odômetro alvo do veículo no vencimento (ex: se o veículo tem 96.000 km e vence em 10.000 km, informe 106.000 km)"),
            "alert_days_before": _("Quantos dias antes da data limite para alertar"),
            "alert_odometer_before": _("Quantos km antes do odômetro limite para alertar"),
        }
        widgets = {
            "due_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
            "due_odometer": forms.NumberInput(attrs={"min": 0, "class": "form-control"}),
            "alert_days_before": forms.NumberInput(attrs={"min": 1}),
            "alert_odometer_before": forms.NumberInput(attrs={"min": 0}),
            "recurrence_interval_months": forms.NumberInput(attrs={"min": 1}),
            "recurrence_interval_km": forms.NumberInput(attrs={"min": 100}),
        }

    def __init__(self, *args, vehicle=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle_param = vehicle
        self.user = user

        if user:
            from apps.vehicles.models import Vehicle
            self.fields["vehicle"].queryset = Vehicle.objects.filter(
                owner_primary=user,
                is_active=True,
            )
            if self.fields["vehicle"].queryset.count() == 1:
                self.initial["vehicle"] = self.fields["vehicle"].queryset.first()

            from apps.maintenance.models import ServiceType
            self.fields["service_type"].queryset = ServiceType.objects.filter(
                is_active=True,
            ).filter(
                models.Q(user=user) | models.Q(user__isnull=True),
            ).order_by("name")

        if vehicle:
            self.initial["vehicle"] = vehicle
            self.fields["vehicle"].widget = forms.HiddenInput()

        self.helper = FormHelper()
        self.helper.form_method = "post"

        vehicle_row = []
        if not vehicle:
            vehicle_row = [
                Fieldset(
                    _("Veículo"),
                    Row(
                        Field("vehicle", css_class="form-select"),
                        css_class="row g-3",
                    ),
                )
            ]

        self.helper.layout = Layout(
            *vehicle_row,
            Fieldset(
                _("Identificação do Lembrete"),
                Row(
                    Field("title", css_class="form-control", placeholder=_("Ex: Troca de Óleo e Filtros")),
                    Field("reminder_type", css_class="form-select"),
                    css_class="row g-3",
                ),
                Row(
                    Field("service_type", css_class="form-select"),
                    css_class="row g-3",
                ),
            ),
            Fieldset(
                _("Critérios de Vencimento (Data ou Odômetro)"),
                Row(
                    Field("due_date", css_class="form-control"),
                    Field("due_odometer", css_class="form-control", placeholder=_("Ex: 106000")),
                    css_class="row g-3",
                ),
                Row(
                    Field("alert_days_before", css_class="form-control"),
                    Field("alert_odometer_before", css_class="form-control"),
                    css_class="row g-3",
                ),
            ),
            Fieldset(
                _("Recorrência e Notificações"),
                Row(
                    Field("is_recurring", css_class="form-check-input"),
                    Field("notify_by_email", css_class="form-check-input"),
                    css_class="row g-3 mb-2",
                ),
                Row(
                    Field("recurrence_interval_months", css_class="form-control", placeholder=_("Ex: 12 meses")),
                    Field("recurrence_interval_km", css_class="form-control", placeholder=_("Ex: 10000 km")),
                    css_class="row g-3",
                ),
            ),
            Fieldset(
                _("Observações"),
                Field("notes", css_class="form-control", rows=3),
            ),
            Submit("submit", _("Salvar Lembrete"), css_class="btn btn-primary mt-3"),
        )

    def clean(self):
        cleaned_data = super().clean()
        due_date = cleaned_data.get("due_date")
        due_odometer = cleaned_data.get("due_odometer")
        vehicle = cleaned_data.get("vehicle") or self.vehicle_param

        if not due_date and not due_odometer:
            raise forms.ValidationError(
                _("Você deve especificar uma data limite ou um odômetro limite (ou ambos).")
            )

        # Smart odometer check: detect if user typed an interval smaller than current vehicle odometer
        if vehicle and due_odometer:
            current_odo = vehicle.current_odometer_cache or 0
            if current_odo > 0 and due_odometer <= current_odo:
                suggested_odo = current_odo + due_odometer
                raise forms.ValidationError(
                    _(
                        f"O odômetro limite informado ({due_odometer:,} km) já foi ultrapassado "
                        f"pela quilometragem atual do veículo ({current_odo:,} km). "
                        f"Para ser avisado daqui a {due_odometer:,} km, informe o odômetro final: {suggested_odo:,} km."
                    )
                )

        is_recurring = cleaned_data.get("is_recurring")
        rec_months = cleaned_data.get("recurrence_interval_months")
        rec_km = cleaned_data.get("recurrence_interval_km")

        if is_recurring and not rec_months and not rec_km:
            raise forms.ValidationError(
                _("Para lembretes recorrentes, informe o intervalo de repetição em meses ou km.")
            )

        return cleaned_data


class CompleteReminderForm(forms.Form):
    """Form to mark a reminder as completed and optionally record maintenance."""

    completion_date = forms.DateField(
        label=_("Data da Conclusão"),
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        initial=timezone.now().date,
    )
    completion_odometer = forms.IntegerField(
        label=_("Odômetro na Conclusão (km)"),
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0}),
    )
    create_maintenance = forms.BooleanField(
        label=_("Registrar como manutenção realizada no histórico?"),
        required=False,
        initial=True,
    )
    total_amount = forms.DecimalField(
        label=_("Valor da Manutenção (R$)"),
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
    )
    workshop_name = forms.CharField(
        label=_("Oficina / Prestador"),
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, reminder=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.reminder = reminder
        if reminder and reminder.vehicle:
            if not self.initial.get("completion_odometer"):
                self.initial["completion_odometer"] = reminder.vehicle.current_odometer_cache

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Field("completion_date", css_class="form-control"),
                Field("completion_odometer", css_class="form-control"),
                css_class="row g-3",
            ),
            Field("create_maintenance", css_class="form-check-input mt-3"),
            Row(
                Field("total_amount", css_class="form-control"),
                Field("workshop_name", css_class="form-control"),
                css_class="row g-3",
            ),
            Submit("submit", _("Confirmar Conclusão"), css_class="btn btn-success mt-3"),
        )

