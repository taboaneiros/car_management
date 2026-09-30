"""
Views for the reminders app.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from apps.maintenance.models import Maintenance, MaintenanceType
from apps.vehicles.models import Vehicle

from .forms import CompleteReminderForm, ReminderForm
from .models import Reminder, ReminderStatus, ReminderType
from .services import ReminderService


class ReminderListView(LoginRequiredMixin, ListView):
    """View for listing vehicle reminders."""

    model = Reminder
    template_name = "reminders/reminder_list.html"
    context_object_name = "reminders"
    paginate_by = 20

    def get_queryset(self):
        tab = self.request.GET.get("tab", "pending")
        vehicle_id = self.request.GET.get("vehicle")

        queryset = Reminder.objects.filter(
            vehicle__owner_primary=self.request.user
        ).select_related("vehicle", "service_type")

        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        if tab == "pending":
            queryset = queryset.filter(status=ReminderStatus.PENDING)
        elif tab == "completed":
            queryset = queryset.filter(status=ReminderStatus.COMPLETED)
        # 'all' includes pending, completed, cancelled

        r_type = self.request.GET.get("type")
        if r_type:
            queryset = queryset.filter(reminder_type=r_type)

        return queryset.order_by("due_date", "due_odometer", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle_id = self.request.GET.get("vehicle")
        active_vehicle = None
        if vehicle_id:
            try:
                active_vehicle = Vehicle.objects.get(
                    id=vehicle_id, owner_primary=self.request.user
                )
            except Vehicle.DoesNotExist:
                pass

        context["vehicles"] = Vehicle.objects.filter(
            owner_primary=self.request.user,
            is_active=True,
        )
        context["current_tab"] = self.request.GET.get("tab", "pending")
        context["reminder_types"] = ReminderType.choices
        context["summary"] = ReminderService.get_user_reminders_summary(
            self.request.user, vehicle=active_vehicle
        )
        return context


class ReminderCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new reminder."""

    model = Reminder
    form_class = ReminderForm
    template_name = "reminders/reminder_form.html"
    success_url = reverse_lazy("reminders:list")

    def dispatch(self, request, *args, **kwargs):
        self.vehicle = None
        vehicle_id = kwargs.get("vehicle_id") or request.GET.get("vehicle")
        if vehicle_id:
            self.vehicle = get_object_or_404(
                Vehicle,
                id=vehicle_id,
                owner_primary=request.user,
                is_active=True,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["vehicle"] = self.vehicle
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicles = Vehicle.objects.filter(owner_primary=self.request.user, is_active=True)
        context["vehicle_odometers"] = {str(v.id): (v.current_odometer_cache or 0) for v in vehicles}
        context["selected_vehicle"] = self.vehicle
        return context

    def form_valid(self, form):
        vehicle = form.cleaned_data.get("vehicle")
        if not vehicle and self.vehicle:
            form.instance.vehicle = self.vehicle
        elif vehicle and vehicle.owner_primary != self.request.user:
            messages.error(self.request, _("Veículo selecionado inválido."))
            return self.form_invalid(form)

        messages.success(self.request, _("Lembrete agendado com sucesso!"))
        return super().form_valid(form)


class ReminderUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating an existing reminder."""

    model = Reminder
    form_class = ReminderForm
    template_name = "reminders/reminder_form.html"
    success_url = reverse_lazy("reminders:list")

    def get_queryset(self):
        return Reminder.objects.filter(
            vehicle__owner_primary=self.request.user
        ).select_related("vehicle")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicles = Vehicle.objects.filter(owner_primary=self.request.user, is_active=True)
        context["vehicle_odometers"] = {str(v.id): (v.current_odometer_cache or 0) for v in vehicles}
        context["selected_vehicle"] = self.object.vehicle
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["vehicle"] = self.object.vehicle
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Lembrete atualizado com sucesso!"))
        return super().form_valid(form)


class ReminderDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting a reminder."""

    model = Reminder
    template_name = "reminders/reminder_confirm_delete.html"
    success_url = reverse_lazy("reminders:list")

    def get_queryset(self):
        return Reminder.objects.filter(vehicle__owner_primary=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Lembrete excluído com sucesso."))
        return super().delete(request, *args, **kwargs)


class ReminderCompleteView(LoginRequiredMixin, View):
    """View for marking a reminder as completed and optionally creating a maintenance record."""

    def get(self, request, pk):
        reminder = get_object_or_404(
            Reminder,
            id=pk,
            vehicle__owner_primary=request.user,
        )
        form = CompleteReminderForm(reminder=reminder)
        return render(
            request,
            "reminders/reminder_complete.html",
            {"reminder": reminder, "form": form},
        )

    def post(self, request, pk):
        reminder = get_object_or_404(
            Reminder,
            id=pk,
            vehicle__owner_primary=request.user,
        )
        form = CompleteReminderForm(request.POST, reminder=reminder)

        if form.is_valid():
            completion_date = form.cleaned_data["completion_date"]
            completion_odometer = form.cleaned_data.get("completion_odometer")
            create_maintenance = form.cleaned_data.get("create_maintenance")
            total_amount = form.cleaned_data.get("total_amount")
            workshop_name = form.cleaned_data.get("workshop_name", "")

            # If user wants to register maintenance
            maintenance = None
            if create_maintenance and reminder.reminder_type == ReminderType.MAINTENANCE:
                maintenance = Maintenance.objects.create(
                    vehicle=reminder.vehicle,
                    service_type=reminder.service_type,
                    maintenance_type=MaintenanceType.PREVENTIVE,
                    occurred_at=completion_date,
                    odometer=completion_odometer or reminder.vehicle.current_odometer_cache or 0,
                    total_amount=total_amount or 0,
                    workshop_name=workshop_name,
                    description=f"Conclusão do lembrete: {reminder.title}",
                    reminder=reminder,
                )

            # Mark reminder completed (which also creates the next recurrence if recurring)
            next_reminder = reminder.mark_as_completed(
                completion_date=completion_date,
                completion_odometer=completion_odometer,
                create_next=True,
            )

            if next_reminder:
                messages.success(
                    request,
                    _(f"Lembrete concluído! Próximo lembrete agendado para {next_reminder.due_date or next_reminder.due_odometer}."),
                )
            else:
                messages.success(request, _("Lembrete concluído com sucesso!"))

            return redirect("reminders:list")

        return render(
            request,
            "reminders/reminder_complete.html",
            {"reminder": reminder, "form": form},
        )

