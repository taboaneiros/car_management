"""
Maintenance models for car_management project.
Handles preventive and corrective maintenance services for vehicles.
"""
import os
import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def maintenance_attachment_upload_path(instance, filename):
    """Generate upload path for maintenance attachments."""
    today = date.today()
    ext = os.path.splitext(filename)[1]
    return f"maintenance/{today.year}/{today.month:02d}/{uuid.uuid4()}{ext}"


class MaintenanceType(models.TextChoices):
    """Types of maintenance interventions."""

    PREVENTIVE = "preventive", _("Preventive")
    CORRECTIVE = "corrective", _("Corrective")


class ServiceType(models.Model):
    """
    Service type / catalog model.
    Represents standardized service categories (e.g. Oil change, Brake pads).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_types",
        verbose_name=_("user"),
        null=True,
        blank=True,
    )
    name = models.CharField(_("name"), max_length=100)
    description = models.TextField(_("description"), blank=True)

    # Recommended intervals
    default_interval_km = models.PositiveIntegerField(
        _("default interval (km)"),
        null=True,
        blank=True,
        help_text=_("Recommended mileage between services"),
    )
    default_interval_months = models.PositiveIntegerField(
        _("default interval (months)"),
        null=True,
        blank=True,
        help_text=_("Recommended months between services"),
    )

    is_system = models.BooleanField(_("system"), default=False)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("service type")
        verbose_name_plural = _("service types")
        db_table = "maintenance_service_type"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return self.name


class Maintenance(models.Model):
    """
    Maintenance record model.
    Represents a specific service or repair performed on a vehicle.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.CASCADE,
        related_name="maintenances",
        verbose_name=_("vehicle"),
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenances",
        verbose_name=_("service type"),
    )
    maintenance_type = models.CharField(
        _("type"),
        max_length=20,
        choices=MaintenanceType.choices,
        default=MaintenanceType.PREVENTIVE,
    )

    occurred_at = models.DateField(_("date"))
    odometer = models.PositiveIntegerField(
        _("odometer (km)"),
        help_text=_("Vehicle odometer at the time of service"),
    )
    total_amount = models.DecimalField(
        _("total amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total cost of maintenance"),
    )
    workshop_name = models.CharField(
        _("workshop / provider"),
        max_length=100,
        blank=True,
        help_text=_("Name of workshop or mechanic"),
    )
    description = models.CharField(
        _("description"),
        max_length=255,
        blank=True,
        help_text=_("Brief description of the service performed"),
    )
    notes = models.TextField(_("notes"), blank=True)
    attachment = models.FileField(
        _("attachment"),
        upload_to=maintenance_attachment_upload_path,
        blank=True,
        null=True,
    )

    # Optional origin reminder
    reminder = models.ForeignKey(
        "reminders.Reminder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenances",
        verbose_name=_("reminder"),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("maintenance")
        verbose_name_plural = _("maintenances")
        db_table = "maintenance_maintenance"
        ordering = ["-occurred_at", "-odometer"]
        indexes = [
            models.Index(fields=["vehicle", "occurred_at"]),
            models.Index(fields=["vehicle", "maintenance_type"]),
        ]

    def __str__(self):
        title = self.service_type.name if self.service_type else self.description or _("Maintenance")
        return f"{self.vehicle.name} - {title} ({self.occurred_at})"

    def save(self, *args, **kwargs):
        """Save maintenance and update vehicle odometer cache and reminder."""
        super().save(*args, **kwargs)

        if self.vehicle and self.odometer:
            self.vehicle.update_odometer_cache(self.odometer)

        if self.reminder and self.reminder.status == "pending":
            self.reminder.mark_as_completed(
                completion_date=self.occurred_at,
                completion_odometer=self.odometer,
            )

    def get_display_amount(self):
        """Format total amount for templates."""
        return f"R$ {self.total_amount:.2f}"

