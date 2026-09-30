"""
Views for the reports app: analytics hub, vehicle comparison, and data exports.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView

from apps.vehicles.models import Vehicle

from .services.analytics_service import VehicleComparisonService
from .services.export_service import ExportService


class ReportsHubView(LoginRequiredMixin, TemplateView):
    """Central dashboard for advanced analytics and reports."""
    template_name = "reports/reports_hub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        vehicles = Vehicle.objects.filter(owner_primary=user, is_active=True)

        selected_vehicle_id = self.request.GET.get("vehicle")
        selected_vehicle = None
        if selected_vehicle_id:
            selected_vehicle = vehicles.filter(id=selected_vehicle_id).first()

        comparison = VehicleComparisonService.get_comparison_data(
            user,
            vehicle_ids=[str(selected_vehicle.id)] if selected_vehicle else None,
        )
        trend = VehicleComparisonService.get_monthly_consumption_trend(
            user, vehicle=selected_vehicle, months=6
        )
        fuel_analytics = VehicleComparisonService.get_monthly_fuel_analytics(
            user, vehicle=selected_vehicle, months=6
        )
        expense_analytics = VehicleComparisonService.get_expense_analytics(
            user, vehicle=selected_vehicle, months=6
        )
        maint_analytics = VehicleComparisonService.get_maintenance_analytics(
            user, vehicle=selected_vehicle, months=6
        )

        context["vehicles"] = vehicles
        context["selected_vehicle"] = selected_vehicle
        context["comparison"] = comparison
        context["trend_labels"] = [t["label"] for t in trend]
        context["trend_values"] = [t["avg_km_l"] for t in trend]
        context["fuel"] = fuel_analytics
        context["expense"] = expense_analytics
        context["maintenance"] = maint_analytics
        return context


class VehicleComparisonView(LoginRequiredMixin, TemplateView):
    """Side-by-side comparison of vehicles."""
    template_name = "reports/vehicle_comparison.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        vehicles = Vehicle.objects.filter(owner_primary=user, is_active=True)

        selected_ids = self.request.GET.getlist("vehicles")
        date_start = self.request.GET.get("date_start")
        date_end = self.request.GET.get("date_end")

        comparison = VehicleComparisonService.get_comparison_data(
            user,
            vehicle_ids=selected_ids if selected_ids else None,
            date_start=date_start if date_start else None,
            date_end=date_end if date_end else None,
        )

        v_data = comparison["vehicles_data"]
        context["vehicles"] = vehicles
        context["selected_ids"] = selected_ids
        context["comparison"] = comparison
        context["date_start"] = date_start or ""
        context["date_end"] = date_end or ""

        # Chart.js datasets
        context["chart_labels"] = [item["vehicle"].name for item in v_data]
        context["chart_tco"] = [float(item["total_tco"]) for item in v_data]
        context["chart_fuel_cost"] = [float(item["fuel_cost"]) for item in v_data]
        context["chart_maint_cost"] = [float(item["maintenance_cost"]) for item in v_data]
        context["chart_exp_cost"] = [float(item["expense_cost"]) for item in v_data]
        context["chart_cost_km"] = [float(item["cost_per_km"]) for item in v_data]
        context["chart_consumption"] = [float(item["avg_consumption"]) for item in v_data]

        return context


class ExportDataView(LoginRequiredMixin, View):
    """View to select criteria and trigger data downloads (CSV/Excel)."""
    template_name = "reports/export_data.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get("download") == "1":
            return self._handle_export(request)

        vehicles = Vehicle.objects.filter(owner_primary=request.user, is_active=True)
        entity = request.GET.get("entity", "consolidated")
        return render(
            request,
            self.template_name,
            {
                "vehicles": vehicles,
                "selected_entity": entity,
            },
        )

    def post(self, request, *args, **kwargs):
        return self._handle_export(request)

    def _handle_export(self, request):
        user = request.user
        entity = request.POST.get("entity") or request.GET.get("entity", "consolidated")
        export_format = request.POST.get("format") or request.GET.get("format", "csv")
        vehicle_id = request.POST.get("vehicle") or request.GET.get("vehicle")
        date_start = request.POST.get("date_start") or request.GET.get("date_start")
        date_end = request.POST.get("date_end") or request.GET.get("date_end")

        vehicle = None
        if vehicle_id:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner_primary=user)

        return ExportService.export(
            user=user,
            entity=entity,
            export_format=export_format,
            vehicle=vehicle,
            date_start=date_start if date_start else None,
            date_end=date_end if date_end else None,
        )


class QuickExportView(LoginRequiredMixin, View):
    """Shortcut endpoint for downloading specific entities directly from list views."""

    def get(self, request, entity, *args, **kwargs):
        export_format = request.GET.get("format", "csv")
        vehicle_id = request.GET.get("vehicle")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")

        vehicle = None
        if vehicle_id:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner_primary=request.user)

        return ExportService.export(
            user=request.user,
            entity=entity,
            export_format=export_format,
            vehicle=vehicle,
            date_start=date_start if date_start else None,
            date_end=date_end if date_end else None,
        )


class PrintReportView(LoginRequiredMixin, TemplateView):
    """Print-friendly view for reports and summaries."""
    template_name = "reports/print_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        vehicle_id = self.request.GET.get("vehicle")
        date_start = self.request.GET.get("date_start")
        date_end = self.request.GET.get("date_end")

        vehicle = None
        if vehicle_id:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner_primary=user)

        comparison = VehicleComparisonService.get_comparison_data(
            user,
            vehicle_ids=[str(vehicle.id)] if vehicle else None,
            date_start=date_start if date_start else None,
            date_end=date_end if date_end else None,
        )

        context["vehicle"] = vehicle
        context["comparison"] = comparison
        context["date_start"] = date_start or ""
        context["date_end"] = date_end or ""
        return context

