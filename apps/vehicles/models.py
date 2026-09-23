"""
Vehicle models for car_management project.
Contains Vehicle and VehicleOwnership models.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class VehicleType(models.TextChoices):
    """Vehicle type choices."""

    CAR = "car", _("Car")
    MOTORCYCLE = "motorcycle", _("Motorcycle")
    TRUCK = "truck", _("Truck")
    VAN = "van", _("Van")
    BUS = "bus", _("Bus")
    OTHER = "other", _("Other")


class FuelControlType(models.TextChoices):
    """Fuel control type choices."""

    SINGLE = "single", _("Single fuel")
    DUAL = "dual", _("Dual fuel (e.g., gasoline + ethanol)")


class OwnershipRole(models.TextChoices):
    """Vehicle ownership role choices."""

    OWNER = "owner", _("Owner")
    EDITOR = "editor", _("Editor")
    VIEWER = "viewer", _("Viewer")


class Vehicle(models.Model):
    """
    Vehicle model.
    Represents a vehicle owned by a user.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Primary owner (for MVP simplicity, but VehicleOwnership supports multiple)
    owner_primary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
        verbose_name=_("primary owner"),
    )

    # Vehicle identification
    name = models.CharField(_("name"), max_length=100)
    brand = models.CharField(_("brand"), max_length=100)
    model = models.CharField(_("model"), max_length=100)
    version = models.CharField(_("version"), max_length=100, blank=True)
    year = models.PositiveIntegerField(_("year"))

    # Registration
    plate = models.CharField(
        _("plate"),
        max_length=20,
        blank=True,
        help_text=_("Vehicle license plate"),
    )
    color = models.CharField(_("color"), max_length=50, blank=True)

    # Type and fuel
    vehicle_type = models.CharField(
        _("vehicle type"),
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.CAR,
    )
    fuel_control_type = models.CharField(
        _("fuel control type"),
        max_length=10,
        choices=FuelControlType.choices,
        default=FuelControlType.SINGLE,
    )

    # Odometer
    initial_odometer = models.PositiveIntegerField(
        _("initial odometer"),
        default=0,
        help_text=_("Odometer reading when vehicle was added"),
    )
    current_odometer_cache = models.PositiveIntegerField(
        _("current odometer"),
        default=0,
        help_text=_("Cached current odometer reading (updated on each record)"),
    )

    # Status
    is_active = models.BooleanField(_("active"), default=True)

    # Additional info
    notes = models.TextField(_("notes"), blank=True)
    photo = models.ImageField(
        _("photo"),
        upload_to="vehicles/",
        blank=True,
        null=True,
    )

    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("vehicle")
        verbose_name_plural = _("vehicles")
        db_table = "vehicles_vehicle"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner_primary", "is_active"]),
            models.Index(fields=["owner_primary", "name"]),
            models.Index(fields=["plate"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.brand} {self.model})"

    def get_display_name(self):
        """Return a friendly display name for the vehicle."""
        return f"{self.brand} {self.model} - {self.name}"

    def update_odometer_cache(self, new_odometer):
        """
        Update the odometer cache if the new value is higher.
        Returns True if updated, False otherwise.
        """
        if new_odometer > self.current_odometer_cache:
            self.current_odometer_cache = new_odometer
            self.save(update_fields=["current_odometer_cache", "updated_at"])
            return True
        return False


class VehicleOwnership(models.Model):
    """
    Vehicle ownership model.
    Represents the relationship between a user and a vehicle.
    Supports multiple users per vehicle with different roles.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="ownerships",
        verbose_name=_("vehicle"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicle_ownerships",
        verbose_name=_("user"),
    )

    # Role and permissions
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=OwnershipRole.choices,
        default=OwnershipRole.OWNER,
    )
    can_view = models.BooleanField(_("can view"), default=True)
    can_edit = models.BooleanField(_("can edit"), default=True)
    can_transfer = models.BooleanField(_("can transfer"), default=False)

    # Status
    is_active = models.BooleanField(_("active"), default=True)
    joined_at = models.DateTimeField(_("joined at"), auto_now_add=True)

    class Meta:
        verbose_name = _("vehicle ownership")
        verbose_name_plural = _("vehicle ownerships")
        db_table = "vehicles_ownership"
        unique_together = ["vehicle", "user"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.vehicle.name} ({self.role})"

    def save(self, *args, **kwargs):
        """Set permissions based on role."""
        if self.role == OwnershipRole.OWNER:
            self.can_view = True
            self.can_edit = True
            self.can_transfer = True
        elif self.role == OwnershipRole.EDITOR:
            self.can_view = True
            self.can_edit = True
            self.can_transfer = False
        elif self.role == OwnershipRole.VIEWER:
            self.can_view = True
            self.can_edit = False
            self.can_transfer = False
        super().save(*args, **kwargs)