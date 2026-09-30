"""
Tests for the maintenance app.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.vehicles.models import Vehicle
from apps.reminders.models import Reminder, ReminderStatus

from .models import Maintenance, MaintenanceType, ServiceType

User = get_user_model()


class MaintenanceModelTests(TestCase):
    """Tests for maintenance models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="maint_user@example.com",
            password="testpass123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Civic",
            brand="Honda",
            model="Civic",
            year=2021,
            initial_odometer=30000,
            current_odometer_cache=30000,
        )
        self.service_type = ServiceType.objects.create(
            name="Troca de Óleo",
            default_interval_km=10000,
            default_interval_months=12,
            is_system=True,
        )

    def test_create_maintenance_updates_vehicle_odometer(self):
        """Creating maintenance with higher odometer updates vehicle odometer cache."""
        maint = Maintenance.objects.create(
            vehicle=self.vehicle,
            service_type=self.service_type,
            maintenance_type=MaintenanceType.PREVENTIVE,
            occurred_at="2026-02-10",
            odometer=35000,
            total_amount=Decimal("350.00"),
            workshop_name="Oficina Central",
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_odometer_cache, 35000)
        self.assertEqual(maint.total_amount, Decimal("350.00"))
        self.assertEqual(maint.get_display_amount(), "R$ 350.00")

    def test_create_maintenance_with_attachment(self):
        """Testing uploading an invoice attachment."""
        pdf_file = SimpleUploadedFile("nota.pdf", b"%PDF-1.4 test invoice", content_type="application/pdf")
        maint = Maintenance.objects.create(
            vehicle=self.vehicle,
            service_type=self.service_type,
            maintenance_type=MaintenanceType.CORRECTIVE,
            occurred_at="2026-02-10",
            odometer=36000,
            total_amount=Decimal("120.00"),
            attachment=pdf_file,
        )
        self.assertTrue(maint.attachment)
        self.assertTrue(maint.attachment.name.endswith(".pdf"))

    def test_maintenance_completes_associated_reminder(self):
        """When maintenance is created with a linked pending reminder, it marks it completed."""
        reminder = Reminder.objects.create(
            vehicle=self.vehicle,
            title="Trocar Óleo",
            service_type=self.service_type,
            due_odometer=35000,
            status=ReminderStatus.PENDING,
        )
        self.assertEqual(reminder.status, ReminderStatus.PENDING)

        Maintenance.objects.create(
            vehicle=self.vehicle,
            service_type=self.service_type,
            maintenance_type=MaintenanceType.PREVENTIVE,
            occurred_at="2026-02-15",
            odometer=35200,
            total_amount=Decimal("300.00"),
            reminder=reminder,
        )
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, ReminderStatus.COMPLETED)
        self.assertEqual(reminder.completed_odometer, 35200)


class MaintenanceViewTests(TestCase):
    """Tests for maintenance views."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="maint_views@example.com",
            password="testpass123",
        )
        self.client.force_login(self.user)
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Tracker",
            brand="Chevrolet",
            model="Tracker",
            year=2022,
            initial_odometer=15000,
            current_odometer_cache=15000,
        )
        self.service_type = ServiceType.objects.create(
            name="Alinhamento",
            user=self.user,
        )

    def test_maintenance_list_view(self):
        """Maintenance list displays records."""
        Maintenance.objects.create(
            vehicle=self.vehicle,
            service_type=self.service_type,
            maintenance_type=MaintenanceType.PREVENTIVE,
            occurred_at="2026-03-01",
            odometer=16000,
            total_amount=Decimal("150.00"),
        )
        response = self.client.get(reverse("maintenance:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tracker")
        self.assertContains(response, "Alinhamento")

    def test_maintenance_create_view(self):
        """User can create maintenance via POST."""
        url = reverse("maintenance:create")
        data = {
            "vehicle": str(self.vehicle.id),
            "service_type": str(self.service_type.id),
            "maintenance_type": MaintenanceType.PREVENTIVE,
            "occurred_at": "2026-03-05",
            "odometer": 17000,
            "total_amount": "200.00",
            "workshop_name": "Oficina do Zé",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Maintenance.objects.count(), 1)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_odometer_cache, 17000)

    def test_service_type_crud(self):
        """User can create and list custom service types."""
        create_url = reverse("maintenance:service_type_create")
        response = self.client.post(
            create_url,
            {"name": "Troca de Pastilha Custom", "default_interval_km": 25000},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ServiceType.objects.filter(name="Troca de Pastilha Custom", user=self.user).exists()
        )

