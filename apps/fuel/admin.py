"""
Admin configuration for the fuel app.
"""
from django.contrib import admin

from .models import FuelType, Refueling


@admin.register(FuelType)
class FuelTypeAdmin(admin.ModelAdmin):
    """
    Admin for the FuelType model.
    """

    list_display = ("name", "code", "user", "is_system", "is_active")
    list_filter = ("is_system", "is_active")
    search_fields = ("name", "code", "user__email")
    raw_id_fields = ("user",)


@admin.register(Refueling)
class RefuelingAdmin(admin.ModelAdmin):
    """
    Admin for the Refueling model.
    """

    list_display = (
        "vehicle",
        "occurred_at",
        "odometer",
        "liters",
        "total_amount",
        "is_full_tank",
        "consumption_km_l",
    )
    list_filter = ("is_full_tank", "is_partial", "is_outlier", "fuel_type")
    search_fields = ("vehicle__name", "station_name")
    raw_id_fields = ("vehicle", "fuel_type")
    readonly_fields = (
        "price_per_liter",
        "consumption_km_l",
        "distance_since_last_full",
        "cost_per_km",
        "is_outlier",
        "created_at",
        "updated_at",
        "id",
    )

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "id",
                "vehicle",
                "occurred_at",
                "station_name",
                "odometer",
            ),
        }),
        ("Fuel Details", {
            "fields": (
                "liters",
                "total_amount",
                "price_per_liter",
                "fuel_type",
            ),
        }),
        ("Tank Status", {
            "fields": (
                "is_full_tank",
                "is_partial",
                "missed_previous_fillup",
            ),
        }),
        ("Calculated Fields", {
            "fields": (
                "consumption_km_l",
                "distance_since_last_full",
                "cost_per_km",
                "is_outlier",
            ),
        }),
        ("Additional", {
            "fields": ("notes", "attachment"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )