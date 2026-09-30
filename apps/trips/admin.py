from django.contrib import admin

from .models import Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle",
        "origin",
        "destination",
        "distance",
        "purpose",
        "started_at",
        "total_cost",
    )
    list_filter = ("purpose", "vehicle", "started_at")
    search_fields = ("origin", "destination", "driver_name", "notes", "vehicle__name")
    date_hierarchy = "started_at"

