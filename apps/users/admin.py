"""
Admin configuration for the users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin for the User model.
    """

    list_display = ("email", "first_name", "last_name", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "username")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin for the UserProfile model.
    """

    list_display = (
        "user",
        "full_name",
        "default_currency",
        "measurement_unit",
        "language",
    )
    list_filter = ("default_currency", "measurement_unit", "language")
    search_fields = ("user__email", "full_name")
    raw_id_fields = ("user",)