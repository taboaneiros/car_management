"""
Dashboard views.
"""
import csv
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse

from apps.expenses.models import Expense
from apps.vehicles.models import Vehicle
from apps.fuel.models import Refueling

from .selectors import DashboardSelectors


@login_required
def dashboard_home(request):
    """
    Main dashboard view.
    """
    user = request.user

    # Get active vehicles
    vehicles = Vehicle.objects.filter(
        owner_primary=user,
        is_active=True,
    ).order_by("name")

    # Get selected vehicle (from session or first vehicle)
    vehicle_id = request.session.get("active_vehicle_id")
    active_vehicle = None

    if vehicle_id:
        try:
            active_vehicle = vehicles.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            pass

    if not active_vehicle and vehicles.exists():
        active_vehicle = vehicles.first()
        request.session["active_vehicle_id"] = str(active_vehicle.id)

    # Get summaries
    month_summary = DashboardSelectors.get_month_summary(user, active_vehicle)
    year_summary = DashboardSelectors.get_year_summary(user, active_vehicle)

    # Get recent records
    recent_refuelings = DashboardSelectors.get_recent_refuelings(
        user, limit=5, vehicle=active_vehicle
    )
    recent_expenses = DashboardSelectors.get_recent_expenses(
        user, limit=5, vehicle=active_vehicle
    )

    # Get chart data
    monthly_costs = DashboardSelectors.get_monthly_costs_chart_data(
        user, months=6, vehicle=active_vehicle
    )
    categories_breakdown = DashboardSelectors.get_expense_categories_breakdown(
        user, vehicle=active_vehicle
    )

    # Vehicle stats
    vehicle_stats = None
    if active_vehicle:
        vehicle_stats = DashboardSelectors.get_vehicle_stats(active_vehicle)

    context = {
        "vehicles": vehicles,
        "active_vehicle": active_vehicle,
        "month_summary": month_summary,
        "year_summary": year_summary,
        "recent_refuelings": recent_refuelings,
        "recent_expenses": recent_expenses,
        "monthly_costs": monthly_costs,
        "categories_breakdown": categories_breakdown,
        "vehicle_stats": vehicle_stats,
    }

    return render(request, "dashboard/home.html", context)


@login_required
def dashboard_cards_partial(request):
    """
    HTMX partial for dashboard cards.
    """
    user = request.user

    # Get active vehicle
    vehicle_id = request.GET.get("vehicle") or request.session.get("active_vehicle_id")
    active_vehicle = None

    if vehicle_id:
        try:
            active_vehicle = Vehicle.objects.get(
                id=vehicle_id,
                owner_primary=user,
                is_active=True,
            )
            request.session["active_vehicle_id"] = str(active_vehicle.id)
        except Vehicle.DoesNotExist:
            pass

    # Get summaries
    month_summary = DashboardSelectors.get_month_summary(user, active_vehicle)
    year_summary = DashboardSelectors.get_year_summary(user, active_vehicle)

    context = {
        "active_vehicle": active_vehicle,
        "month_summary": month_summary,
        "year_summary": year_summary,
    }

    return render(request, "dashboard/partials/cards.html", context)


@login_required
def set_active_vehicle(request, vehicle_id):
    """
    Set the active vehicle in session.
    """
    vehicle = get_object_or_404(
        Vehicle,
        id=vehicle_id,
        owner_primary=request.user,
        is_active=True,
    )

    request.session["active_vehicle_id"] = str(vehicle.id)

    # Check if HTMX request
    if request.headers.get("HX-Request"):
        return dashboard_cards_partial(request)

    return JsonResponse({"status": "ok", "vehicle_id": str(vehicle.id)})


@login_required
def consumption_chart_data(request):
    """
    JSON data for consumption chart.
    """
    user = request.user
    vehicle_id = request.GET.get("vehicle") or request.session.get("active_vehicle_id")

    active_vehicle = None
    if vehicle_id:
        try:
            active_vehicle = Vehicle.objects.get(
                id=vehicle_id,
                owner_primary=user,
                is_active=True,
            )
        except Vehicle.DoesNotExist:
            pass

    monthly_costs = DashboardSelectors.get_monthly_costs_chart_data(
        user, months=6, vehicle=active_vehicle
    )

    return JsonResponse(monthly_costs, safe=False)


@login_required
def export_refuelings_csv(request):
    """Export user's refuelings to a CSV file."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="refuelings.csv"'

    response.write("\ufeff")  # BOM for Excel

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "vehicle",
        "odometer",
        "date",
        "fuel_type",
        "price_per_liter",
        "total_amount",
        "liters",
        "is_full_tank",
        "station_name",
    ])

    queryset = Refueling.objects.filter(
        vehicle__owner_primary=request.user
    ).select_related("vehicle", "fuel_type")

    for item in queryset.order_by("occurred_at", "odometer"):
        writer.writerow([
            item.vehicle.name,
            item.odometer,
            item.occurred_at.isoformat(),
            item.fuel_type.name if item.fuel_type else "",
            item.price_per_liter or "",
            item.total_amount,
            item.liters,
            "Sim" if item.is_full_tank else "Não",
            item.station_name,
        ])

    return response


@login_required
def export_expenses_csv(request):
    """Export user's expenses to a CSV file."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="expenses.csv"'

    response.write("\ufeff")  # BOM for Excel

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "vehicle", "date", "description", "category", "amount", "odometer"
    ])

    queryset = Expense.objects.filter(
        vehicle__owner_primary=request.user
    ).select_related("vehicle", "category")

    for item in queryset.order_by("occurred_at"):
        writer.writerow([
            item.vehicle.name, item.occurred_at.isoformat(), item.description,
            item.category.name if item.category else "", item.amount, item.odometer or ""
        ])

    return response


@login_required
def costs_chart_data(request):
    """
    JSON data for costs chart.
    """
    user = request.user
    vehicle_id = request.GET.get("vehicle") or request.session.get("active_vehicle_id")

    active_vehicle = None
    if vehicle_id:
        try:
            active_vehicle = Vehicle.objects.get(
                id=vehicle_id,
                owner_primary=user,
                is_active=True,
            )
        except Vehicle.DoesNotExist:
            pass

    monthly_costs = DashboardSelectors.get_monthly_costs_chart_data(
        user, months=6, vehicle=active_vehicle
    )

    return JsonResponse(monthly_costs, safe=False)