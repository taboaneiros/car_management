"""
Tests for the reminders app.
"""
from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.maintenance.models import Maintenance, ServiceType
from apps.vehicles.models import Vehicle

from .models import Reminder, ReminderStatus, ReminderType
from .services import ReminderService

User = get_user_model()


class ReminderModelTests(TestCase):
    """Tests for the Reminder model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="reminder_test@example.com",
            password="testpass123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Corolla",
            brand="Toyota",
            model="Corolla",
            year=2020,
            initial_odometer=50000,
            current_odometer_cache=50000,
        )

    def test_validation_requires_date_or_odometer(self):
        """At least one of due_date or due_odometer is required."""
        reminder = Reminder(
            vehicle=self.vehicle,
            title="Lembrete Sem Alvo",
        )
        with self.assertRaises(ValidationError):
            reminder.clean()

    def test_date_urgency_calculation(self):
        """Test urgency calculation based on due_date."""
        today = timezone.now().date()

        # Overdue
        r_overdue = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Vencido por Data",
            due_date=today - timedelta(days=2),
        )
        self.assertTrue(r_overdue.is_overdue())
        self.assertFalse(r_overdue.is_due_soon())
        self.assertEqual(r_overdue.urgency, "overdue")

        # Due soon (within 15 days)
        r_soon = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Próximo por Data",
            due_date=today + timedelta(days=5),
            alert_days_before=15,
        )
        self.assertFalse(r_soon.is_overdue())
        self.assertTrue(r_soon.is_due_soon())
        self.assertEqual(r_soon.urgency, "due_soon")

        # Ok (far in future)
        r_ok = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Futuro por Data",
            due_date=today + timedelta(days=40),
            alert_days_before=15,
        )
        self.assertFalse(r_ok.is_overdue())
        self.assertFalse(r_ok.is_due_soon())
        self.assertEqual(r_ok.urgency, "ok")

    def test_odometer_urgency_calculation(self):
        """Test urgency calculation based on vehicle current odometer cache."""
        # Vehicle is at 50,000 km

        # Overdue (target 49,000)
        r_overdue = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Vencido por km",
            due_odometer=49000,
        )
        self.assertTrue(r_overdue.is_overdue())
        self.assertEqual(r_overdue.urgency, "overdue")

        # Due soon (target 50,300 km with alert_odometer_before=500 km)
        r_soon = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Próximo por km",
            due_odometer=50300,
            alert_odometer_before=500,
        )
        self.assertFalse(r_soon.is_overdue())
        self.assertTrue(r_soon.is_due_soon())
        self.assertEqual(r_soon.urgency, "due_soon")

        # Ok (target 60,000 km)
        r_ok = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Futuro por km",
            due_odometer=60000,
            alert_odometer_before=500,
        )
        self.assertFalse(r_ok.is_overdue())
        self.assertFalse(r_ok.is_due_soon())
        self.assertEqual(r_ok.urgency, "ok")

    def test_dual_criteria_whichever_first(self):
        """When both date and km are specified, urgency triggers if either condition is met."""
        today = timezone.now().date()
        # Date is far (ok), but km is reached (overdue)
        r = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Duplo - km atingido primeiro",
            due_date=today + timedelta(days=60),
            due_odometer=50000,
        )
        self.assertTrue(r.is_overdue())
        self.assertEqual(r.urgency, "overdue")

    def test_mark_as_completed_creates_next_recurrence(self):
        """Completing a recurring reminder automatically schedules the next recurrence."""
        today = timezone.now().date()
        reminder = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Revisão Periódica",
            due_date=today,
            due_odometer=50000,
            is_recurring=True,
            recurrence_interval_months=6,
            recurrence_interval_km=10000,
        )

        next_reminder = reminder.mark_as_completed(
            completion_date=today,
            completion_odometer=50000,
            create_next=True,
        )

        reminder.refresh_from_db()
        self.assertEqual(reminder.status, ReminderStatus.COMPLETED)
        self.assertIsNotNone(next_reminder)
        self.assertEqual(next_reminder.due_odometer, 60000)
        self.assertEqual(next_reminder.status, ReminderStatus.PENDING)
        self.assertTrue(next_reminder.is_recurring)


class ReminderServiceAndNotificationTests(TestCase):
    """Tests for ReminderService and email notification dispatch."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="notif_user@example.com",
            password="testpass123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Onix",
            brand="Chevrolet",
            model="Onix",
            year=2023,
            initial_odometer=10000,
            current_odometer_cache=10000,
        )

    def test_send_reminder_email(self):
        """Test sending email notification for a reminder."""
        reminder = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Troca de Pastilhas",
            due_odometer=9900,  # Overdue
            notify_by_email=True,
        )
        sent = ReminderService.send_reminder_email(reminder)
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertIn("Onix", email.subject)
        self.assertIn("Troca de Pastilhas", email.subject)
        self.assertIn(self.user.email, email.to)
        self.assertIn("10000 km", email.body)

        reminder.refresh_from_db()
        self.assertIsNotNone(reminder.last_notified_at)

    def test_check_notifications_throttling(self):
        """Test that notification service respects 24-hour throttling."""
        reminder = Reminder.objects.create(
            vehicle=self.vehicle,
            title="IPVA",
            due_date=timezone.now().date(),
            notify_by_email=True,
        )

        # First run sends 1 email
        res1 = ReminderService.check_and_send_notifications(user=self.user)
        self.assertEqual(res1["sent_count"], 1)
        self.assertEqual(len(mail.outbox), 1)

        # Immediate second run is throttled
        res2 = ReminderService.check_and_send_notifications(user=self.user)
        self.assertEqual(res2["sent_count"], 0)
        self.assertEqual(res2["skipped_count"], 1)

        # Force bypasses throttling
        res3 = ReminderService.check_and_send_notifications(user=self.user, force=True)
        self.assertEqual(res3["sent_count"], 1)
        self.assertEqual(len(mail.outbox), 2)


class ReminderViewTests(TestCase):
    """Tests for reminder views."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="view_user@example.com",
            password="testpass123",
        )
        self.client.force_login(self.user)
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Yaris",
            brand="Toyota",
            model="Yaris",
            year=2021,
            initial_odometer=20000,
            current_odometer_cache=20000,
        )

    def test_reminder_create_and_list_views(self):
        """Create a reminder through view and list it."""
        url = reverse("reminders:create")
        data = {
            "vehicle": str(self.vehicle.id),
            "title": "Troca de Pneus",
            "reminder_type": ReminderType.MAINTENANCE,
            "due_odometer": 25000,
            "alert_days_before": 15,
            "alert_odometer_before": 500,
            "notify_by_email": True,
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Reminder.objects.count(), 1)

        list_res = self.client.get(reverse("reminders:list"))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "Troca de Pneus")

    def test_complete_reminder_with_maintenance_creation(self):
        """Completing a reminder can also create a maintenance record."""
        service_type = ServiceType.objects.create(name="Troca de Pneus")
        reminder = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Troca de Pneus",
            service_type=service_type,
            due_odometer=20000,
            status=ReminderStatus.PENDING,
        )

        complete_url = reverse("reminders:complete", kwargs={"pk": reminder.id})
        data = {
            "completion_date": "2026-03-10",
            "completion_odometer": 20100,
            "create_maintenance": True,
            "total_amount": "1200.00",
            "workshop_name": "Pneustore",
        }
        res = self.client.post(complete_url, data)
        self.assertEqual(res.status_code, 302)

        reminder.refresh_from_db()
        self.assertEqual(reminder.status, ReminderStatus.COMPLETED)
        self.assertTrue(
            Maintenance.objects.filter(
                vehicle=self.vehicle,
                reminder=reminder,
                total_amount=1200.00,
            ).exists()
        )

    def test_check_reminders_command(self):
        """Testing management command check_reminders."""
        out = StringIO()
        call_command("check_reminders", dry_run=True, stdout=out)
        self.assertIn("Check complete", out.getvalue())

