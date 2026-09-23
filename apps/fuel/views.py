"""
Views for the fuel app.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.utils.translation import gettext as _
from apps.vehicles.models import Vehicle

from .calculators import ConsumptionCalculator
from .forms import RefuelingForm
from .models import Refueling


class RefuelingListView(LoginRequiredMixin, ListView):
    """
    View for listing refuelings.
    """

    model = Refueling
    template_name = "fuel/refueling_list.html"
    context_object_name = "refuelings"
    paginate_by = 20

    def get_queryset(self):
        """Return refuelings for the user's vehicles."""
        queryset = Refueling.objects.filter(
            vehicle__owner_primary=self.request.user,
        ).select_related("vehicle", "fuel_type")

        # Filter by vehicle if specified
        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        # Filter by date range
        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")
        if start_date:
            queryset = queryset.filter(occurred_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(occurred_at__lte=end_date)

        return queryset.order_by("-occurred_at", "-odometer")

    def get_context_data(self, **kwargs):
        """Add vehicles to context for filtering."""
        context = super().get_context_data(**kwargs)
        context["vehicles"] = Vehicle.objects.filter(
            owner_primary=self.request.user,
            is_active=True,
        )
        context["selected_vehicle"] = self.request.GET.get("vehicle")
        return context


class RefuelingCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new refueling.
    """

    model = Refueling
    form_class = RefuelingForm
    template_name = "fuel/refueling_form.html"
    success_url = reverse_lazy("fuel:list")

    def dispatch(self, request, *args, **kwargs):
        """Check if user has at least one vehicle."""
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
        """Pass vehicle and user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["vehicle"] = self.vehicle
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Set the vehicle and calculate consumption."""
        # Get vehicle from form (selected by user or passed via URL)
        vehicle = form.cleaned_data.get("vehicle")
        
        if not vehicle:
            messages.error(self.request, _("No vehicle specified."))
            return redirect("vehicles:list")

        # The vehicle is already set by the form since it's in fields
        # But we ensure it's set on the instance
        form.instance.vehicle = vehicle
        
        response = super().form_valid(form)

        # Update vehicle odometer cache
        vehicle.update_odometer_cache(form.instance.odometer)

        # Calculate consumption
        ConsumptionCalculator.update_refueling_consumption(self.object)

        messages.success(
            self.request,
            f'Abastecimento registrado com sucesso.',
        )
        return response

    def get_context_data(self, **kwargs):
        """Add vehicle to context."""
        context = super().get_context_data(**kwargs)
        context["vehicle"] = self.vehicle
        return context


class RefuelingUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating a refueling.
    """

    model = Refueling
    form_class = RefuelingForm
    template_name = "fuel/refueling_form.html"
    success_url = reverse_lazy("fuel:list")

    def get_queryset(self):
        """Return only the user's refuelings."""
        return Refueling.objects.filter(
            vehicle__owner_primary=self.request.user,
        ).select_related("vehicle")

    def get_form_kwargs(self):
        """Pass vehicle and user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["vehicle"] = self.object.vehicle
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)

        # Update vehicle odometer cache
        self.object.vehicle.update_odometer_cache(form.instance.odometer)

        # Recalculate consumption for this and subsequent refuelings
        ConsumptionCalculator.update_refueling_consumption(self.object)
        ConsumptionCalculator.recalculate_vehicle_consumption(self.object.vehicle)

        messages.success(
            self.request,
            f'Abastecimento atualizado com sucesso.',
        )
        return response


class RefuelingDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting a refueling.
    """

    model = Refueling
    template_name = "fuel/refueling_confirm_delete.html"
    success_url = reverse_lazy("fuel:list")

    def get_queryset(self):
        """Return only the user's refuelings."""
        return Refueling.objects.filter(
            vehicle__owner_primary=self.request.user,
        ).select_related("vehicle")

    def delete(self, request, *args, **kwargs):
        """Delete and recalculate consumption."""
        self.object = self.get_object()
        vehicle = self.object.vehicle
        self.object.delete()

        # Recalculate consumption for remaining refuelings
        ConsumptionCalculator.recalculate_vehicle_consumption(vehicle)

        messages.success(
            request,
            f'Abastecimento removido com sucesso.',
        )
        return redirect(self.success_url)


class RefuelingListPartialView(LoginRequiredMixin, ListView):
    """
    Partial view for HTMX filtering of refuelings.
    """

    model = Refueling
    template_name = "fuel/partials/refueling_list_rows.html"
    context_object_name = "refuelings"
    paginate_by = 20

    def get_queryset(self):
        """Return refuelings for the user's vehicles."""
        queryset = Refueling.objects.filter(
            vehicle__owner_primary=self.request.user,
        ).select_related("vehicle", "fuel_type")

        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")
        if start_date:
            queryset = queryset.filter(occurred_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(occurred_at__lte=end_date)

        return queryset.order_by("-occurred_at", "-odometer")