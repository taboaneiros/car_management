"""
Services for the reminders app.
Handles status evaluation, categorization, and email dispatch.
"""
from datetime import timedelta
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import Reminder, ReminderStatus

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminder status and notifications."""

    @staticmethod
    def get_user_reminders(user, vehicle=None, status=None):
        """
        Get queryset of reminders for a user, optionally filtered by vehicle and status.
        """
        queryset = Reminder.objects.filter(
            vehicle__owner_primary=user
        ).select_related("vehicle", "service_type")

        if vehicle:
            queryset = queryset.filter(vehicle=vehicle)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    @classmethod
    def get_user_reminders_summary(cls, user, vehicle=None):
        """
        Categorize active reminders into overdue, due_soon, and upcoming.
        """
        pending = cls.get_user_reminders(
            user, vehicle=vehicle, status=ReminderStatus.PENDING
        )

        overdue_list = []
        due_soon_list = []
        ok_list = []

        for reminder in pending:
            if reminder.is_overdue():
                overdue_list.append(reminder)
            elif reminder.is_due_soon():
                due_soon_list.append(reminder)
            else:
                ok_list.append(reminder)

        return {
            "overdue": overdue_list,
            "due_soon": due_soon_list,
            "ok": ok_list,
            "total_pending": len(overdue_list) + len(due_soon_list) + len(ok_list),
            "overdue_count": len(overdue_list),
            "due_soon_count": len(due_soon_list),
            "has_alerts": bool(overdue_list or due_soon_list),
        }

    @staticmethod
    def send_reminder_email(reminder):
        """
        Send a notification email for a specific reminder.
        """
        user = reminder.vehicle.owner_primary
        if not user.email:
            logger.warning("Cannot send reminder email: User %s has no email address.", user)
            return False

        is_overdue = reminder.is_overdue()
        status_label = _("VENCIDO") if is_overdue else _("PRÓXIMO DO VENCIMENTO")
        subject = f"[{status_label}] Lembrete: {reminder.title} - {reminder.vehicle.name}"

        context = {
            "user": user,
            "reminder": reminder,
            "vehicle": reminder.vehicle,
            "is_overdue": is_overdue,
            "status_label": status_label,
            "site_url": getattr(settings, "SITE_URL", "http://localhost:8000"),
        }

        text_content = render_to_string("emails/reminder_alert.txt", context)
        html_content = render_to_string("emails/reminder_alert.html", context)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        reminder.last_notified_at = timezone.now()
        reminder.save(update_fields=["last_notified_at", "updated_at"])
        return True

    @classmethod
    def check_and_send_notifications(cls, user=None, force=False, dry_run=False):
        """
        Check all pending reminders and send email alerts when due or overdue.
        Throttles sending to at most once per 24 hours unless force=True.
        """
        queryset = Reminder.objects.filter(
            status=ReminderStatus.PENDING,
            notify_by_email=True,
        ).select_related("vehicle", "vehicle__owner_primary", "service_type")

        if user:
            queryset = queryset.filter(vehicle__owner_primary=user)

        sent_count = 0
        skipped_count = 0
        now = timezone.now()
        throttle_window = now - timedelta(hours=24)

        for reminder in queryset:
            if not (reminder.is_overdue() or reminder.is_due_soon()):
                continue

            # Throttle check
            if not force and reminder.last_notified_at and reminder.last_notified_at > throttle_window:
                skipped_count += 1
                continue

            if dry_run:
                sent_count += 1
                logger.info("[Dry Run] Would send email for reminder: %s", reminder)
            else:
                try:
                    if cls.send_reminder_email(reminder):
                        sent_count += 1
                except Exception as exc:
                    logger.error("Failed to send reminder email for %s: %s", reminder, exc)

        return {
            "sent_count": sent_count,
            "skipped_count": skipped_count,
        }

