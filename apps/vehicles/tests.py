"""
Tests for the vehicles app.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import OwnershipRole, Vehicle, VehicleOwnership

User = get_user_model()


class VehicleModelTests(TestCase):
    """Tests for the Vehicle model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="vehicle@example.com",
            password="testpass123",
        )

    def test_create_vehicle(self):
        """Test creating a vehicle."""
        vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Meu Carro",
            brand="Toyota",
            model="Corolla",
            year=2020,
            initial_odometer=10000,
        )
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertEqual(vehicle.owner_primary, self.user)
        self.assertEqual(vehicle.current_odometer_cache, 0)
        self.assertTrue(vehicle.is_active)

    def test_update_odometer_cache(self):
        """Test updating the odometer cache."""
        vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Meu Carro",
            brand="Toyota",
            model="Corolla",
            year=2020,
            initial_odometer=10000,
        )
        updated = vehicle.update_odometer_cache(15000)
        self.assertTrue(updated)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.current_odometer_cache, 15000)

        # Lower value should not update
        updated = vehicle.update_odometer_cache(12000)
        self.assertFalse(updated)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.current_odometer_cache, 15000)

    def test_create_ownership(self):
        """Test creating a vehicle ownership record."""
        vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Meu Carro",
            brand="Toyota",
            model="Corolla",
            year=2020,
        )
        ownership = VehicleOwnership.objects.create(
            vehicle=vehicle,
            user=self.user,
            role=OwnershipRole.OWNER,
        )
        self.assertEqual(ownership.role, OwnershipRole.OWNER)
        self.assertTrue(ownership.can_view)
        self.assertTrue(ownership.can_edit)
        self.assertTrue(ownership.can_transfer)


class VehicleViewTests(TestCase):
    """Tests for vehicle views."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="vehicleview@example.com",
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

    def test_vehicle_list_requires_login(self):
        """Test that the vehicle list requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("vehicles:list"))
        self.assertEqual(response.status_code, 302)

    def test_vehicle_list_renders(self):
        """Test that the vehicle list renders."""
        response = self.client.get(reverse("vehicles:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "vehicles/vehicle_list.html")

    def test_vehicle_detail_renders(self):
        """Test that the vehicle detail renders."""
        response = self.client.get(
            reverse("vehicles:detail", args=[self.vehicle.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "vehicles/vehicle_detail.html")
        self.assertIn("total_spent", response.context)
        self.assertIn("avg_consumption", response.context)

    def test_vehicle_create_renders(self):
        """Test that the vehicle create form renders."""
        response = self.client.get(reverse("vehicles:create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "vehicles/vehicle_form.html")

    def test_vehicle_create(self):
        """Test creating a vehicle via the form."""
        response = self.client.post(
            reverse("vehicles:create"),
            {
                "name": "Segundo Carro",
                "brand": "Honda",
                "model": "Civic",
                "year": 2021,
                "initial_odometer": 5000,
                "vehicle_type": "car",
                "fuel_control_type": "single",
            },

        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vehicle.objects.count(), 2)
        vehicle = Vehicle.objects.get(name="Segundo Carro")
        self.assertEqual(vehicle.owner_primary, self.user)
        # Ownership record should be created
        self.assertTrue(
            VehicleOwnership.objects.filter(
                vehicle=vehicle,
                user=self.user,
                role=OwnershipRole.OWNER,
            ).exists()
        )

    def test_vehicle_delete_soft_delete(self):
        """Test that deleting a vehicle performs a soft delete."""
        response = self.client.post(
            reverse("vehicles:delete", args=[self.vehicle.id])
        )
        self.assertEqual(response.status_code, 302)
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.is_active)
