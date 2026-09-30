"""
Admin configuration for the maintenance app.
"""
from django.contrib import admin

from .models import Maintenance, ServiceType


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    """Admin for ServiceType model."""

    list_display = (
        "name",
        "user",
        "default_interval_km",
        "default_interval_months",
        "is_system",
        "is_active",
    )
    list_filter = ("is_system", "is_active")
    search_fields = ("name", "description", "user__email")
    raw_id_fields = ("user",)


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    """Admin for Maintenance model."""

    list_display = (
        "vehicle",
        "service_type",
        "maintenance_type",
        "occurred_at",
        "odometer",
        "total_amount",
        "workshop_name",
    )
    list_filter = ("maintenance_type", "occurred_at")
    search_fields = ("vehicle__name", "description", "workshop_name", "service_type__name")
    raw_id_fields = ("vehicle", "service_type", "reminder")
    readonly_fields = ("created_at", "updated_at", "id")

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "id",
                "vehicle",
                "service_type",
                "maintenance_type",
                "occurred_at",
                "odometer",
                "total_amount",
            ),
        }),
        ("Details", {
            "fields": (
                "workshop_name",
                "description",
                "reminder",
            ),
        }),
        ("Additional", {
            "fields": ("notes", "attachment"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

