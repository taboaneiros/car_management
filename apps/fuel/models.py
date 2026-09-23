"""
Fuel models for car_management project.
Contains FuelType and Refueling models with consumption calculation support.
"""
import os
import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def fuel_attachment_upload_path(instance, filename):
    """Generate upload path for fuel attachments."""
    today = date.today()
    ext = os.path.splitext(filename)[1]
    return f"fuel/{today.year}/{today.month:02d}/{uuid.uuid4()}{ext}"


class FuelType(models.Model):
    """
    Fuel type model.
    Represents different types of fuel (gasoline, ethanol, diesel, etc.).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fuel_types",
        verbose_name=_("user"),
        null=True,
        blank=True,
    )
    name = models.CharField(_("name"), max_length=50)
    code = models.CharField(_("code"), max_length=10, blank=True)

    # System fuel types are available to all users
    is_system = models.BooleanField(_("system"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("fuel type")
        verbose_name_plural = _("fuel types")
        db_table = "fuel_fuel_type"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return self.name


class Refueling(models.Model):
    """
    Refueling model.
    Represents a fuel refueling event with consumption calculation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.CASCADE,
        related_name="refuelings",
        verbose_name=_("vehicle"),
    )

    # Refueling details
    occurred_at = models.DateField(_("date"))
    station_name = models.CharField(
        _("station name"),
        max_length=100,
        blank=True,
        help_text=_("Name of the gas station"),
    )
    odometer = models.PositiveIntegerField(
        _("odometer (km)"),
        help_text=_("Current odometer reading"),
    )

    # Fuel quantities and prices
    liters = models.DecimalField(
        _("liters"),
        max_digits=8,
        decimal_places=3,
        help_text=_("Amount of fuel in liters"),
    )
    total_amount = models.DecimalField(
        _("total amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total amount paid"),
    )
    price_per_liter = models.DecimalField(
        _("price per liter"),
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        help_text=_("Price per liter (calculated if not provided)"),
    )

    fuel_type = models.ForeignKey(
        FuelType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refuelings",
        verbose_name=_("fuel type"),
    )

    # Tank status
    is_full_tank = models.BooleanField(
        _("full tank"),
        default=True,
        help_text=_("Was the tank filled to full?"),
    )
    is_partial = models.BooleanField(
        _("partial"),
        default=False,
        help_text=_("Was this a partial refueling?"),
    )
    missed_previous_fillup = models.BooleanField(
        _("missed previous fillup"),
        default=False,
        help_text=_("Did you miss recording the previous full tank?"),
    )

    # Notes and attachment
    notes = models.TextField(_("notes"), blank=True)
    attachment = models.FileField(
        _("attachment"),
        upload_to=fuel_attachment_upload_path,
        blank=True,
        null=True,
    )

    # Calculated fields (populated by calculators)
    consumption_km_l = models.DecimalField(
        _("consumption (km/l)"),
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("Calculated fuel consumption in km/l"),
    )
    distance_since_last_full = models.PositiveIntegerField(
        _("distance since last full"),
        blank=True,
        null=True,
        help_text=_("Distance traveled since last full tank"),
    )
    cost_per_km = models.DecimalField(
        _("cost per km"),
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        help_text=_("Cost per kilometer"),
    )
    is_outlier = models.BooleanField(
        _("outlier"),
        default=False,
        help_text=_("Is this consumption an outlier?"),
    )

    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("refueling")
        verbose_name_plural = _("refuelings")
        db_table = "fuel_refueling"
        ordering = ["-occurred_at", "-odometer"]
        indexes = [
            models.Index(fields=["vehicle", "occurred_at"]),
            models.Index(fields=["vehicle", "odometer"]),
            models.Index(fields=["vehicle", "is_full_tank", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.vehicle.name} - {self.occurred_at} - {self.liters}L"

    def save(self, *args, **kwargs):
        """
        Calculate derived fields automatically.
        
        Priority:
        1. If total_amount is provided and price_per_liter is not, calculate price_per_liter
        2. If price_per_liter and liters are provided but total_amount is not, calculate total_amount
        3. If all three are provided, keep them as is (user may want specific values)
        """
        # Calculate total_amount from liters * price_per_liter if total_amount not set
        if not self.total_amount and self.liters and self.price_per_liter:
            self.total_amount = self.liters * self.price_per_liter
        
        # Calculate price_per_liter from total_amount / liters if price_per_liter not set
        if not self.price_per_liter and self.liters and self.total_amount:
            self.price_per_liter = self.total_amount / self.liters
        
        super().save(*args, **kwargs)

    def get_display_price(self):
        """Return formatted price per liter."""
        if self.price_per_liter:
            return f"R$ {self.price_per_liter:.4f}"
        return "-"

    def get_display_consumption(self):
        """Return formatted consumption."""
        if self.consumption_km_l:
            return f"{self.consumption_km_l:.2f} km/l"
        return "-"