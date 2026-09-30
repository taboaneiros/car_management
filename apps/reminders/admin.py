"""
Admin configuration for the reminders app.
"""
from django.contrib import admin

from .models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    """Admin for Reminder model."""

    list_display = (
        "vehicle",
        "title",
        "reminder_type",
        "status",
        "due_date",
        "due_odometer",
        "is_recurring",
        "notify_by_email",
    )
    list_filter = ("status", "reminder_type", "is_recurring", "notify_by_email")
    search_fields = ("title", "vehicle__name", "notes")
    raw_id_fields = ("vehicle", "service_type")
    readonly_fields = ("created_at", "updated_at", "id", "last_notified_at")

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "id",
                "vehicle",
                "title",
                "reminder_type",
                "service_type",
                "status",
            ),
        }),
        ("Due Targets", {
            "fields": (
                "due_date",
                "due_odometer",
                "alert_days_before",
                "alert_odometer_before",
            ),
        }),
        ("Recurrence", {
            "fields": (
                "is_recurring",
                "recurrence_interval_months",
                "recurrence_interval_km",
            ),
        }),
        ("Completion", {
            "fields": (
                "completed_at",
                "completed_odometer",
            ),
        }),
        ("Notification & Notes", {
            "fields": (
                "notify_by_email",
                "last_notified_at",
                "notes",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

