"""
Views for the vehicles app.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView


from .forms import VehicleForm
from .models import OwnershipRole, Vehicle, VehicleOwnership


class VehicleListView(LoginRequiredMixin, ListView):
    """
    View for listing user's vehicles.
    """

    model = Vehicle
    template_name = "vehicles/vehicle_list.html"
    context_object_name = "vehicles"
    paginate_by = 10

    def get_queryset(self):
        """Return only the user's vehicles."""
        return Vehicle.objects.filter(
            owner_primary=self.request.user,
            is_active=True,
        ).order_by("-created_at")


class VehicleDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying vehicle details.
    """

    model = Vehicle
    template_name = "vehicles/vehicle_detail.html"
    context_object_name = "vehicle"

    def get_queryset(self):
        """Return only the user's vehicles."""
        return Vehicle.objects.filter(owner_primary=self.request.user)

    def get_context_data(self, **kwargs):
        """Add vehicle stats and recent records to context."""
        context = super().get_context_data(**kwargs)
        vehicle = self.object

        # Total spent (refuelings + expenses)
        total_refuelings = vehicle.refuelings.aggregate(
            total=models.Sum("total_amount")
        )["total"] or 0
        total_expenses = vehicle.expenses.aggregate(
            total=models.Sum("amount")
        )["total"] or 0
        context["total_spent"] = total_refuelings + total_expenses

        # Average consumption
        consumption = vehicle.refuelings.exclude(
            consumption_km_l__isnull=True
        ).aggregate(avg=models.Avg("consumption_km_l"))["avg"]
        context["avg_consumption"] = consumption or 0

        # Recent records
        context["recent_refuelings"] = vehicle.refuelings.select_related(
            "fuel_type"
        ).order_by("-occurred_at", "-odometer")[:5]
        context["recent_expenses"] = vehicle.expenses.select_related(
            "category"
        ).order_by("-occurred_at")[:5]

        return context



class VehicleCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new vehicle.
    """

    model = Vehicle
    form_class = VehicleForm
    template_name = "vehicles/vehicle_form.html"
    success_url = reverse_lazy("vehicles:list")

    def form_valid(self, form):
        """Set the owner to the current user and create ownership."""
        form.instance.owner_primary = self.request.user
        form.instance.current_odometer_cache = form.instance.initial_odometer
        response = super().form_valid(form)

        # Create ownership record
        VehicleOwnership.objects.create(
            vehicle=self.object,
            user=self.request.user,
            role=OwnershipRole.OWNER,
        )

        messages.success(
            self.request,
            f'Veículo "{self.object.name}" criado com sucesso.',
        )
        return response


class VehicleUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating a vehicle.
    """

    model = Vehicle
    form_class = VehicleForm
    template_name = "vehicles/vehicle_form.html"
    success_url = reverse_lazy("vehicles:list")

    def get_queryset(self):
        """Return only the user's vehicles."""
        return Vehicle.objects.filter(owner_primary=self.request.user)

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Veículo "{self.object.name}" atualizado com sucesso.',
        )
        return response


class VehicleDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting a vehicle.
    Soft delete by setting is_active to False.
    """

    model = Vehicle
    template_name = "vehicles/vehicle_confirm_delete.html"
    success_url = reverse_lazy("vehicles:list")

    def get_queryset(self):
        """Return only the user's vehicles."""
        return Vehicle.objects.filter(owner_primary=self.request.user)

    def form_valid(self, form):
        """Soft delete the vehicle by setting is_active to False."""
        self.object.is_active = False
        self.object.save(update_fields=["is_active", "updated_at"])
        messages.success(
            self.request,
            f'Veículo "{self.object.name}" removido com sucesso.',
        )
        return redirect(self.get_success_url())




class VehicleActivateView(LoginRequiredMixin, DetailView):
    """
    View for setting a vehicle as the active vehicle in the session.
    """

    model = Vehicle

    def get_queryset(self):
        """Return only the user's vehicles."""
        return Vehicle.objects.filter(owner_primary=self.request.user)

    def post(self, request, *args, **kwargs):
        """Set the vehicle as active in the session."""
        vehicle = self.get_object()
        request.session["active_vehicle_id"] = str(vehicle.id)
        messages.success(
            request,
            f'Veículo "{vehicle.name}" selecionado como ativo.',
        )
        # Redirect to the referer or dashboard
        referer = request.META.get("HTTP_REFERER", reverse("dashboard:home"))
        return redirect(referer)