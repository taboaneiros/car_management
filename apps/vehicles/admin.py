"""
Admin configuration for the vehicles app.
"""
from django.contrib import admin

from .models import Vehicle, VehicleOwnership


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """
    Admin for the Vehicle model.
    """

    list_display = (
        "name",
        "brand",
        "model",
        "year",
        "plate",
        "owner_primary",
        "is_active",
        "current_odometer_cache",
    )
    list_filter = ("is_active", "vehicle_type", "fuel_control_type", "year")
    search_fields = ("name", "brand", "model", "plate", "owner_primary__email")
    raw_id_fields = ("owner_primary",)
    readonly_fields = ("created_at", "updated_at", "id")

    fieldsets = (
        ("Identification", {
            "fields": (
                "id",
                "owner_primary",
                "name",
                "brand",
                "model",
                "version",
                "year",
                "plate",
                "color",
            ),
        }),
        ("Type and Fuel", {
            "fields": ("vehicle_type", "fuel_control_type"),
        }),
        ("Odometer", {
            "fields": ("initial_odometer", "current_odometer_cache"),
        }),
        ("Additional", {
            "fields": ("notes", "photo", "is_active"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


@admin.register(VehicleOwnership)
class VehicleOwnershipAdmin(admin.ModelAdmin):
    """
    Admin for the VehicleOwnership model.
    """

    list_display = ("vehicle", "user", "role", "can_view", "can_edit", "can_transfer", "is_active")
    list_filter = ("role", "is_active", "can_view", "can_edit", "can_transfer")
    search_fields = ("vehicle__name", "user__email")
    raw_id_fields = ("vehicle", "user")
    readonly_fields = ("joined_at", "id")