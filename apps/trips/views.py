"""
Views for the trips app.
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.vehicles.models import Vehicle

from .forms import TripForm
from .models import Trip, TripPurpose


class TripListView(LoginRequiredMixin, ListView):
    """List of trips with filtering and summary metrics."""
    model = Trip
    template_name = "trips/trip_list.html"
    context_object_name = "trips"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Trip.objects.filter(vehicle__owner_primary=self.request.user)
            .select_related("vehicle")
            .order_by("-started_at")
        )

        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)

        purpose = self.request.GET.get("purpose")
        if purpose:
            qs = qs.filter(purpose=purpose)

        date_start = self.request.GET.get("date_start")
        if date_start:
            qs = qs.filter(started_at__date__gte=date_start)

        date_end = self.request.GET.get("date_end")
        if date_end:
            qs = qs.filter(started_at__date__lte=date_end)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        metrics = qs.aggregate(
            total_km=Sum("distance"),
            total_cost=Sum("total_cost"),
            trips_count=Count("id"),
        )
        context["total_km"] = metrics["total_km"] or Decimal("0")
        context["total_cost"] = metrics["total_cost"] or Decimal("0")
        context["trips_count"] = metrics["trips_count"] or 0

        context["vehicles"] = Vehicle.objects.filter(
            owner_primary=self.request.user, is_active=True
        )
        context["purposes"] = TripPurpose.choices
        context["selected_vehicle"] = self.request.GET.get("vehicle", "")
        context["selected_purpose"] = self.request.GET.get("purpose", "")
        context["date_start"] = self.request.GET.get("date_start", "")
        context["date_end"] = self.request.GET.get("date_end", "")
        return context


class TripDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a trip."""
    model = Trip
    template_name = "trips/trip_detail.html"
    context_object_name = "trip"

    def get_queryset(self):
        return Trip.objects.filter(
            vehicle__owner_primary=self.request.user
        ).select_related("vehicle")


class TripCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new trip."""
    model = Trip
    form_class = TripForm
    template_name = "trips/trip_form.html"
    success_message = "Viagem registrada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            kwargs["vehicle"] = get_object_or_404(
                Vehicle, id=vehicle_id, owner_primary=self.request.user
            )
        return kwargs

    def get_success_url(self):
        return reverse_lazy("trips:detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Nova Viagem"
        return context


class TripUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Edit an existing trip."""
    model = Trip
    form_class = TripForm
    template_name = "trips/trip_form.html"
    success_message = "Viagem atualizada com sucesso!"

    def get_queryset(self):
        return Trip.objects.filter(
            vehicle__owner_primary=self.request.user
        ).select_related("vehicle")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("trips:detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Editar Viagem"
        return context


class TripDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete a trip."""
    model = Trip
    template_name = "trips/trip_confirm_delete.html"
    context_object_name = "trip"
    success_url = reverse_lazy("trips:list")
    success_message = "Viagem excluída com sucesso."

    def get_queryset(self):
        return Trip.objects.filter(vehicle__owner_primary=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

