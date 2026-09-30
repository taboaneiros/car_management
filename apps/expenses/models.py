"""
Expense models for car_management project.
Contains ExpenseCategory and Expense models.
"""
import os
import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def expense_attachment_upload_path(instance, filename):
    """Generate upload path for expense attachments."""
    today = date.today()
    ext = os.path.splitext(filename)[1]
    return f"expenses/{today.year}/{today.month:02d}/{uuid.uuid4()}{ext}"


class CategoryKind(models.TextChoices):
    """Expense category kind choices."""

    FIXED = "fixed", _("Fixed")
    VARIABLE = "variable", _("Variable")
    OTHER = "other", _("Other")


class ExpenseCategory(models.Model):
    """
    Expense category model.
    Represents categories for organizing expenses.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expense_categories",
        verbose_name=_("user"),
        null=True,
        blank=True,
    )
    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), max_length=100)
    kind = models.CharField(
        _("kind"),
        max_length=20,
        choices=CategoryKind.choices,
        default=CategoryKind.VARIABLE,
    )

    # System categories are available to all users
    is_system = models.BooleanField(_("system"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("expense category")
        verbose_name_plural = _("expense categories")
        db_table = "expenses_category"
        ordering = ["name"]
        # SQLite treats NULL values as distinct in UNIQUE constraints, so
        # system categories (user=None) can share slugs with user-created
        # categories without conflict.
        unique_together = ["user", "slug"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]



    def __str__(self):
        return self.name


class Expense(models.Model):
    """
    Expense model.
    Represents a vehicle expense (parking, toll, fine, etc.).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.CASCADE,
        related_name="expenses",
        verbose_name=_("vehicle"),
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name=_("category"),
    )

    # Expense details
    occurred_at = models.DateField(_("date"))
    amount = models.DecimalField(
        _("amount"),
        max_digits=10,
        decimal_places=2,
    )
    description = models.CharField(
        _("description"),
        max_length=255,
        blank=True,
    )
    odometer = models.PositiveIntegerField(
        _("odometer (km)"),
        blank=True,
        null=True,
        help_text=_("Odometer reading at the time of expense"),
    )
    vendor_name = models.CharField(
        _("vendor"),
        max_length=100,
        blank=True,
        help_text=_("Name of the vendor or establishment"),
    )

    # Recurring expense flag
    is_recurring = models.BooleanField(
        _("recurring"),
        default=False,
        help_text=_("Is this a recurring expense?"),
    )

    # Notes and attachment
    notes = models.TextField(_("notes"), blank=True)
    attachment = models.FileField(
        _("attachment"),
        upload_to=expense_attachment_upload_path,
        blank=True,
        null=True,
    )

    # Optional link to reminder (for recurring expenses)
    reminder = models.ForeignKey(
        "reminders.Reminder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name=_("reminder"),
    )


    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("expense")
        verbose_name_plural = _("expenses")
        db_table = "expenses_expense"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["vehicle", "occurred_at"]),
            models.Index(fields=["vehicle", "category", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.vehicle.name} - {self.occurred_at} - R$ {self.amount}"

    def get_display_amount(self):
        """Return formatted amount."""
        return f"R$ {self.amount:.2f}"