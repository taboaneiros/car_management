"""
Views for the maintenance app.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.vehicles.models import Vehicle

from .forms import MaintenanceForm, ServiceTypeForm
from .models import Maintenance, MaintenanceType, ServiceType


class MaintenanceListView(LoginRequiredMixin, ListView):
    """View for listing vehicle maintenances."""

    model = Maintenance
    template_name = "maintenance/maintenance_list.html"
    context_object_name = "maintenances"
    paginate_by = 20

    def get_queryset(self):
        queryset = Maintenance.objects.filter(
            vehicle__owner_primary=self.request.user,
        ).select_related("vehicle", "service_type")

        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        service_type_id = self.request.GET.get("service_type")
        if service_type_id:
            queryset = queryset.filter(service_type_id=service_type_id)

        m_type = self.request.GET.get("maintenance_type")
        if m_type:
            queryset = queryset.filter(maintenance_type=m_type)

        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")
        if start_date:
            queryset = queryset.filter(occurred_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(occurred_at__lte=end_date)

        return queryset.order_by("-occurred_at", "-odometer")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vehicles"] = Vehicle.objects.filter(
            owner_primary=self.request.user,
            is_active=True,
        )
        context["service_types"] = ServiceType.objects.filter(
            is_active=True,
        ).filter(
            models.Q(user=self.request.user) | models.Q(user__isnull=True),
        ).order_by("name")
        context["maintenance_types"] = MaintenanceType.choices

        # Aggregate total cost for filtered queryset
        qs = self.get_queryset()
        context["total_maintenance_cost"] = (
            qs.aggregate(models.Sum("total_amount"))["total_amount__sum"] or 0
        )
        return context


class MaintenanceCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new maintenance record."""

    model = Maintenance
    form_class = MaintenanceForm
    template_name = "maintenance/maintenance_form.html"
    success_url = reverse_lazy("maintenance:list")

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

    def form_valid(self, form):
        vehicle = form.cleaned_data.get("vehicle")
        if not vehicle and self.vehicle:
            form.instance.vehicle = self.vehicle
        elif vehicle and vehicle.owner_primary != self.request.user:
            messages.error(self.request, _("Invalid vehicle selected."))
            return self.form_invalid(form)

        messages.success(self.request, _("Maintenance recorded successfully!"))
        return super().form_valid(form)


class MaintenanceUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating an existing maintenance record."""

    model = Maintenance
    form_class = MaintenanceForm
    template_name = "maintenance/maintenance_form.html"
    success_url = reverse_lazy("maintenance:list")

    def get_queryset(self):
        return Maintenance.objects.filter(
            vehicle__owner_primary=self.request.user
        ).select_related("vehicle")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["vehicle"] = self.object.vehicle
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Maintenance updated successfully!"))
        return super().form_valid(form)


class MaintenanceDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting a maintenance record."""

    model = Maintenance
    template_name = "maintenance/maintenance_confirm_delete.html"
    success_url = reverse_lazy("maintenance:list")

    def get_queryset(self):
        return Maintenance.objects.filter(vehicle__owner_primary=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Maintenance record deleted."))
        return super().delete(request, *args, **kwargs)


class MaintenanceDetailView(LoginRequiredMixin, DetailView):
    """View for viewing maintenance details."""

    model = Maintenance
    template_name = "maintenance/maintenance_detail.html"
    context_object_name = "maintenance"

    def get_queryset(self):
        return Maintenance.objects.filter(
            vehicle__owner_primary=self.request.user
        ).select_related("vehicle", "service_type", "reminder")


class ServiceTypeListView(LoginRequiredMixin, ListView):
    """View for listing service types."""

    model = ServiceType
    template_name = "maintenance/service_type_list.html"
    context_object_name = "service_types"

    def get_queryset(self):
        return ServiceType.objects.filter(
            models.Q(user=self.request.user) | models.Q(user__isnull=True),
            is_active=True,
        ).order_by("is_system", "name")


class ServiceTypeCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new service type."""

    model = ServiceType
    form_class = ServiceTypeForm
    template_name = "maintenance/service_type_form.html"
    success_url = reverse_lazy("maintenance:service_type_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.is_system = False
        messages.success(self.request, _("Service type created successfully!"))
        return super().form_valid(form)


class ServiceTypeUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating a user-created service type."""

    model = ServiceType
    form_class = ServiceTypeForm
    template_name = "maintenance/service_type_form.html"
    success_url = reverse_lazy("maintenance:service_type_list")

    def get_queryset(self):
        return ServiceType.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _("Service type updated successfully!"))
        return super().form_valid(form)

