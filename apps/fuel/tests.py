"""
Tests for the fuel app.
"""
import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.vehicles.models import Vehicle

from .models import FuelType, Refueling

User = get_user_model()


class FuelModelTests(TestCase):
    """Tests for fuel models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="fuel@example.com",
            password="testpass123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Meu Carro",
            brand="Toyota",
            model="Corolla",
            year=2020,
            initial_odometer=10000,
        )

    def test_create_refueling(self):
        """Test creating a refueling record."""
        refueling = Refueling.objects.create(
            vehicle=self.vehicle,
            occurred_at="2026-01-15",
            odometer=10500,
            liters=40.000,
            total_amount=200.00,
            price_per_liter=5.00,
            is_full_tank=True,
        )
        self.assertEqual(Refueling.objects.count(), 1)
        self.assertEqual(refueling.vehicle, self.vehicle)
        self.assertEqual(refueling.liters, 40.000)
        self.assertEqual(refueling.total_amount, 200.00)

    def test_refueling_calculates_price_per_liter(self):
        """Test that price_per_liter is calculated when not provided."""
        refueling = Refueling.objects.create(
            vehicle=self.vehicle,
            occurred_at="2026-01-15",
            odometer=10500,
            liters=40.000,
            total_amount=200.00,
        )
        self.assertIsNotNone(refueling.price_per_liter)
        self.assertEqual(float(refueling.price_per_liter), 5.0)

    def test_refueling_calculates_total_amount(self):
        """Test that total_amount is calculated when not provided."""
        refueling = Refueling.objects.create(
            vehicle=self.vehicle,
            occurred_at="2026-01-15",
            odometer=10500,
            liters=40.000,
            price_per_liter=5.00,
        )
        self.assertIsNotNone(refueling.total_amount)
        self.assertEqual(float(refueling.total_amount), 200.0)

    def test_refueling_accepts_pdf_attachment(self):
        """Test that a PDF attachment can be uploaded to a refueling."""
        pdf_content = b"%PDF-1.4 test pdf content"
        attachment = SimpleUploadedFile(
            "nota.pdf",
            pdf_content,
            content_type="application/pdf",
        )
        refueling = Refueling.objects.create(
            vehicle=self.vehicle,
            occurred_at="2026-01-15",
            odometer=10500,
            liters=40.000,
            total_amount=200.00,
            attachment=attachment,
        )
        self.assertTrue(refueling.attachment)
        self.assertTrue(refueling.attachment.name.endswith(".pdf"))

    def test_refueling_accepts_image_attachment(self):
        """Test that an image attachment can be uploaded to a refueling."""
        image_content = b"\x89PNG\r\n\x1a\n fake image content"
        attachment = SimpleUploadedFile(
            "foto.png",
            image_content,
            content_type="image/png",
        )
        refueling = Refueling.objects.create(
            vehicle=self.vehicle,
            occurred_at="2026-01-15",
            odometer=10500,
            liters=40.000,
            total_amount=200.00,
            attachment=attachment,
        )
        self.assertTrue(refueling.attachment)
        self.assertTrue(refueling.attachment.name.endswith(".png"))


class FuelTypeSystemRecordTests(TestCase):
    """Tests for system fuel types being available to all users."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="fueltype@example.com",
            password="testpass123",
        )

    def test_system_fuel_types_exist(self):
        """Test that system fuel types are created by data migration."""
        system_types = FuelType.objects.filter(is_system=True)
        self.assertGreaterEqual(system_types.count(), 1)
        # Gasoline should be one of the system types
        self.assertTrue(
            system_types.filter(code="gasoline").exists()
            or system_types.filter(name__icontains="gasolina").exists()
        )

    def test_system_fuel_types_available_to_user(self):
        """Test that system fuel types (user=None) are visible to a user."""
        system_types = FuelType.objects.filter(
            is_active=True,
            user__isnull=True,
        )
        self.assertGreaterEqual(system_types.count(), 1)

    def test_user_can_create_own_fuel_type(self):
        """Test that a user can create their own fuel type."""
        fuel_type = FuelType.objects.create(
            user=self.user,
            name="Combustível Personalizado",
            code="custom",
        )
        self.assertEqual(fuel_type.user, self.user)
        self.assertFalse(fuel_type.is_system)


class RefuelingViewTests(TestCase):
    """Tests for refueling views."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="refuelview@example.com",
            password="testpass123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Meu Carro",
            brand="Toyota",
            model="Corolla",
            year=2020,
            initial_odometer=10000,
        )
        self.client.login(email=self.user.email, password="testpass123")

    def test_refueling_list_requires_login(self):
        """Test that the refueling list requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("fuel:list"))
        self.assertEqual(response.status_code, 302)

    def test_refueling_list_renders(self):
        """Test that the refueling list renders for an authenticated user."""
        response = self.client.get(reverse("fuel:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "fuel/refueling_list.html")

    def test_refueling_create_renders(self):
        """Test that the refueling create form renders."""
        response = self.client.get(reverse("fuel:create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "fuel/refueling_form.html")

    def test_refueling_create_with_pdf(self):
        """Test creating a refueling with a PDF attachment via the form."""
        pdf_content = b"%PDF-1.4 test pdf content"
        attachment = SimpleUploadedFile(
            "nota.pdf",
            pdf_content,
            content_type="application/pdf",
        )
        response = self.client.post(
            reverse("fuel:create"),
            {
                "vehicle": self.vehicle.id,
                "occurred_at": "2026-01-15",
                "odometer": 10500,
                "liters": "40.000",
                "total_amount": "200.00",
                "price_per_liter": "5.00",
                "is_full_tank": "on",
                "attachment": attachment,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Refueling.objects.count(), 1)
        refueling = Refueling.objects.first()
        self.assertTrue(refueling.attachment)
        self.assertTrue(refueling.attachment.name.endswith(".pdf"))
