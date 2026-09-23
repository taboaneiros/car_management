from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path(
        "set-active-vehicle/<uuid:vehicle_id>/",
        views.set_active_vehicle,
        name="set_active_vehicle",
    ),
    path(
        "partials/cards/",
        views.dashboard_cards_partial,
        name="dashboard_cards_partial",
    ),
    path(
        "charts/consumption/",
        views.consumption_chart_data,
        name="consumption_chart_data",
    ),
    path(
        "charts/costs/",
        views.costs_chart_data,
        name="costs_chart_data",
    ),
    # Export URLs
    path(
        "exports/refuelings.csv",
        views.export_refuelings_csv,
        name="export_refuelings_csv",
    ),
    path(
        "exports/expenses.csv",
        views.export_expenses_csv,
        name="export_expenses_csv",
    ),
]