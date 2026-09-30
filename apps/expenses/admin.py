"""
Admin configuration for the expenses app.
"""
from django.contrib import admin

from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """
    Admin for the ExpenseCategory model.
    """

    list_display = ("name", "slug", "kind", "user", "is_system", "is_active")
    list_filter = ("kind", "is_system", "is_active")
    search_fields = ("name", "slug", "user__email")
    raw_id_fields = ("user",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """
    Admin for the Expense model.
    """

    list_display = (
        "vehicle",
        "category",
        "occurred_at",
        "amount",
        "description",
        "is_recurring",
    )
    list_filter = ("category", "is_recurring")
    search_fields = ("vehicle__name", "description", "vendor_name")
    raw_id_fields = ("vehicle", "category", "reminder")
    readonly_fields = ("created_at", "updated_at", "id")

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "id",
                "vehicle",
                "category",
                "occurred_at",
                "amount",
            ),
        }),
        ("Details", {
            "fields": (
                "description",
                "odometer",
                "vendor_name",
                "is_recurring",
            ),
        }),
        ("Additional", {
            "fields": ("notes", "attachment", "reminder"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )