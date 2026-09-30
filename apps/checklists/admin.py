from django.contrib import admin

from .models import (
    ChecklistInspection,
    ChecklistInspectionItem,
    ChecklistTemplate,
    ChecklistTemplateItem,
)


class ChecklistTemplateItemInline(admin.TabularInline):
    model = ChecklistTemplateItem
    extra = 1


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "is_system", "is_active", "created_at")
    list_filter = ("is_system", "is_active")
    search_fields = ("name", "description")
    inlines = [ChecklistTemplateItemInline]


class ChecklistInspectionItemInline(admin.TabularInline):
    model = ChecklistInspectionItem
    extra = 0


@admin.register(ChecklistInspection)
class ChecklistInspectionAdmin(admin.ModelAdmin):
    list_display = ("title", "vehicle", "status", "odometer", "checked_at")
    list_filter = ("status", "vehicle", "checked_at")
    search_fields = ("title", "notes", "vehicle__name")
    inlines = [ChecklistInspectionItemInline]

