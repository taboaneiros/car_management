"""
Reminder models for car_management project.
Handles scheduled reminders by date and/or odometer with recurrence support.
"""
import calendar
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def add_months(source_date: date, months: int) -> date:
    """Add months to a date, capping day at end of target month."""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)



class ReminderType(models.TextChoices):
    """Types of reminders."""

    MAINTENANCE = "maintenance", _("Maintenance")
    EXPENSE = "expense", _("Expense / Tax")
    DOCUMENT = "document", _("Document / License")
    OTHER = "other", _("Other")


class ReminderStatus(models.TextChoices):
    """Reminder execution status."""

    PENDING = "pending", _("Pending")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


class Reminder(models.Model):
    """
    Reminder model for scheduled vehicle tasks.
    Can trigger by date, odometer, or whichever happens first.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.CASCADE,
        related_name="reminders",
        verbose_name=_("vehicle"),
    )

    title = models.CharField(_("title"), max_length=150)
    reminder_type = models.CharField(
        _("reminder type"),
        max_length=20,
        choices=ReminderType.choices,
        default=ReminderType.MAINTENANCE,
    )
    service_type = models.ForeignKey(
        "maintenance.ServiceType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reminders",
        verbose_name=_("service type"),
        help_text=_("Associated maintenance service type (if applicable)"),
    )

    # Targets (at least one should be defined)
    due_date = models.DateField(
        _("due date"),
        null=True,
        blank=True,
        help_text=_("Date when the reminder is due"),
    )
    due_odometer = models.PositiveIntegerField(
        _("due odometer (km)"),
        null=True,
        blank=True,
        help_text=_("Odometer reading when the reminder is due"),
    )

    # Warning thresholds
    alert_days_before = models.PositiveIntegerField(
        _("alert days before"),
        default=15,
        help_text=_("Number of days before due date to start alerting"),
    )
    alert_odometer_before = models.PositiveIntegerField(
        _("alert km before"),
        default=500,
        help_text=_("Number of kilometers before due odometer to start alerting"),
    )

    # Recurrence
    is_recurring = models.BooleanField(
        _("recurring"),
        default=False,
        help_text=_("Automatically create next reminder when completed?"),
    )
    recurrence_interval_months = models.PositiveIntegerField(
        _("interval (months)"),
        null=True,
        blank=True,
        help_text=_("Recurrence interval in months"),
    )
    recurrence_interval_km = models.PositiveIntegerField(
        _("interval (km)"),
        null=True,
        blank=True,
        help_text=_("Recurrence interval in kilometers"),
    )

    # Status & Completion
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=ReminderStatus.choices,
        default=ReminderStatus.PENDING,
    )
    completed_at = models.DateField(
        _("completed at"),
        null=True,
        blank=True,
    )
    completed_odometer = models.PositiveIntegerField(
        _("completed odometer"),
        null=True,
        blank=True,
    )

    # Notifications
    notify_by_email = models.BooleanField(
        _("notify by email"),
        default=True,
        help_text=_("Send email notification when due or overdue"),
    )
    last_notified_at = models.DateTimeField(
        _("last notified at"),
        null=True,
        blank=True,
    )

    notes = models.TextField(_("notes"), blank=True)

    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("reminder")
        verbose_name_plural = _("reminders")
        db_table = "reminders_reminder"
        ordering = ["due_date", "due_odometer", "-created_at"]
        indexes = [
            models.Index(fields=["vehicle", "status"]),
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["status", "due_odometer"]),
        ]

    def __str__(self):
        return f"{self.vehicle.name} - {self.title} ({self.get_status_display()})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.due_date and not self.due_odometer:
            raise ValidationError(
                _("You must specify either a due date or a due odometer (or both).")
            )

    def is_overdue(self, target_date=None, current_odometer=None):
        """Check if reminder is overdue by date or odometer."""
        if self.status != ReminderStatus.PENDING:
            return False

        target_date = target_date or timezone.now().date()
        current_odometer = (
            current_odometer
            if current_odometer is not None
            else (self.vehicle.current_odometer_cache or 0)
        )

        overdue_date = self.due_date is not None and target_date >= self.due_date
        overdue_odo = (
            self.due_odometer is not None and current_odometer >= self.due_odometer
        )

        return overdue_date or overdue_odo

    def is_due_soon(self, target_date=None, current_odometer=None):
        """Check if reminder is within alert window (and not overdue)."""
        if self.status != ReminderStatus.PENDING:
            return False
        if self.is_overdue(target_date, current_odometer):
            return False

        target_date = target_date or timezone.now().date()
        current_odometer = (
            current_odometer
            if current_odometer is not None
            else (self.vehicle.current_odometer_cache or 0)
        )

        due_soon_date = False
        if self.due_date is not None:
            alert_date = self.due_date - timedelta(days=self.alert_days_before)
            due_soon_date = alert_date <= target_date < self.due_date

        due_soon_odo = False
        if self.due_odometer is not None:
            alert_odo = max(0, self.due_odometer - self.alert_odometer_before)
            due_soon_odo = alert_odo <= current_odometer < self.due_odometer

        return due_soon_date or due_soon_odo

    @property
    def urgency(self):
        """Returns 'overdue', 'due_soon', 'ok', or 'completed'."""
        if self.status == ReminderStatus.COMPLETED:
            return "completed"
        if self.status == ReminderStatus.CANCELLED:
            return "cancelled"
        if self.is_overdue():
            return "overdue"
        if self.is_due_soon():
            return "due_soon"
        return "ok"

    def mark_as_completed(self, completion_date=None, completion_odometer=None, create_next=True):
        """
        Mark reminder as completed and optionally generate the next cycle if recurring.
        """
        self.status = ReminderStatus.COMPLETED
        self.completed_at = completion_date or timezone.now().date()
        if completion_odometer is not None:
            self.completed_odometer = completion_odometer
        elif self.vehicle:
            self.completed_odometer = self.vehicle.current_odometer_cache
        self.save(update_fields=["status", "completed_at", "completed_odometer", "updated_at"])

        if self.is_recurring and create_next:
            return self._create_next_recurrence()
        return None

    def _create_next_recurrence(self):
        """Create next recurring reminder based on intervals."""
        next_due_date = None
        if self.recurrence_interval_months:
            base_date = self.completed_at or self.due_date or timezone.now().date()
            next_due_date = add_months(base_date, self.recurrence_interval_months)

        next_due_odometer = None
        if self.recurrence_interval_km:
            base_odo = (
                self.completed_odometer
                or self.due_odometer
                or (self.vehicle.current_odometer_cache if self.vehicle else 0)
            )
            next_due_odometer = base_odo + self.recurrence_interval_km

        return Reminder.objects.create(
            vehicle=self.vehicle,
            title=self.title,
            reminder_type=self.reminder_type,
            service_type=self.service_type,
            due_date=next_due_date,
            due_odometer=next_due_odometer,
            alert_days_before=self.alert_days_before,
            alert_odometer_before=self.alert_odometer_before,
            is_recurring=True,
            recurrence_interval_months=self.recurrence_interval_months,
            recurrence_interval_km=self.recurrence_interval_km,
            status=ReminderStatus.PENDING,
            notify_by_email=self.notify_by_email,
            notes=self.notes,
        )
