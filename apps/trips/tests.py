"""
Tests for the trips app.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.vehicles.models import Vehicle

from .models import Trip, TripPurpose

User = get_user_model()


class TripModelTests(TestCase):
    """Unit tests for the Trip model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="trip_user@example.com",
            password="testpassword123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Carro Teste",
            year=2020,
            initial_odometer=10000,
            current_odometer_cache=10000,
        )

    def test_trip_auto_computes_distance_and_cost(self):
        """Distance is derived from end - start odometer, and cost from distance * rate."""
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            started_at=timezone.now(),
            start_odometer=10000,
            end_odometer=10250,
            origin="São Paulo",
            destination="Campinas",
            purpose=TripPurpose.BUSINESS,
            rate_per_km=Decimal("0.50"),
        )
        self.assertEqual(trip.distance, Decimal("250"))
        self.assertEqual(trip.total_cost, Decimal("125.00"))

        # Vehicle odometer cache updated to 10250
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_odometer_cache, 10250)

    def test_trip_validation_end_odometer_less_than_start(self):
        """Validation error if end_odometer is less than start_odometer."""
        trip = Trip(
            vehicle=self.vehicle,
            started_at=timezone.now(),
            start_odometer=10000,
            end_odometer=9900,
            origin="A",
            destination="B",
        )
        with self.assertRaises(ValidationError):
            trip.full_clean()

    def test_trip_validation_ended_at_before_started_at(self):
        """Validation error if ended_at is before started_at."""
        now = timezone.now()
        trip = Trip(
            vehicle=self.vehicle,
            started_at=now,
            ended_at=now - timezone.timedelta(hours=1),
            start_odometer=10000,
            end_odometer=10100,
            origin="A",
            destination="B",
        )
        with self.assertRaises(ValidationError):
            trip.full_clean()


class TripViewTests(TestCase):
    """View tests for Trip CRUD operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="trip_views@example.com",
            password="testpassword123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Sedan",
            year=2022,
            initial_odometer=50000,
            current_odometer_cache=50000,
        )
        self.client.login(email=self.user.email, password="testpassword123")

    def test_trip_list_and_create(self):
        """Test listing trips and creating a new trip via POST."""
        list_url = reverse("trips:list")
        res = self.client.get(list_url)
        self.assertEqual(res.status_code, 200)

        create_url = reverse("trips:create")
        post_data = {
            "vehicle": str(self.vehicle.id),
            "origin": "Curitiba",
            "destination": "Florianópolis",
            "purpose": TripPurpose.PERSONAL,
            "started_at": "2026-09-22T08:00",
            "ended_at": "2026-09-22T12:00",
            "start_odometer": 50000,
            "end_odometer": 50300,
            "rate_per_km": "",
            "total_cost": "",
            "driver_name": "Carlos",
            "freight_amount": "",
            "notes": "Passeio",
        }
        res = self.client.post(create_url, post_data)
        self.assertEqual(res.status_code, 302)

        self.assertEqual(Trip.objects.count(), 1)
        trip = Trip.objects.first()
        self.assertEqual(trip.origin, "Curitiba")
        self.assertEqual(trip.destination, "Florianópolis")
        self.assertEqual(trip.distance, Decimal("300"))

