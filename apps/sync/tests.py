"""
Unit and integration tests for apps.sync (PWA, offline data, and batch sync API).
"""
import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.vehicles.models import Vehicle
from apps.fuel.models import Refueling, FuelType
from apps.expenses.models import Expense, ExpenseCategory
from apps.maintenance.models import Maintenance, ServiceType
from apps.reminders.models import Reminder
from apps.checklists.models import ChecklistInspection, ChecklistTemplate, ChecklistTemplateItem
from apps.trips.models import Trip

from .services import SyncProcessingService

User = get_user_model()


class SyncAppTests(TestCase):
    """Test suite for offline synchronization service and endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="sync_tester@example.com",
            password="testpassword123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Carro PWA",
            brand="Toyota",
            model="Corolla",
            year=2023,
            initial_odometer=10000,
            current_odometer_cache=10000,
        )
        self.fuel_type = FuelType.objects.create(
            user=self.user,
            name="Gasolina Comum",
            code="GAS",
        )
        self.category = ExpenseCategory.objects.create(
            user=self.user,
            name="Estacionamento",
            slug="estacionamento",
            kind="variable",
        )
        self.service_type = ServiceType.objects.create(
            name="Troca de Óleo",
            description="Troca de óleo do motor",
            default_interval_km=10000,
        )
        self.template = ChecklistTemplate.objects.create(
            name="Inspeção Rápida",
            description="Teste PWA",
            is_system=True,
        )
        ChecklistTemplateItem.objects.create(
            template=self.template,
            category="Fluidos",
            title="Nível de Óleo",
            order=1,
            is_required=True,
        )

        self.client.login(email=self.user.email, password="testpassword123")

    def test_pwa_manifest_view(self):
        """Manifest returns 200 and valid JSON."""
        res = self.client.get(reverse("sync:pwa_manifest"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["name"], "Car Management")
        self.assertEqual(data["display"], "standalone")
        self.assertTrue(len(data["icons"]) >= 2)

    def test_service_worker_view(self):
        """Service Worker is served with appropriate JS header and root scope."""
        res = self.client.get(reverse("sync:pwa_sw"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/javascript", res["Content-Type"])
        self.assertEqual(res["Service-Worker-Allowed"], "/")
        self.assertIn("cm-pwa-v1", res.content.decode("utf-8"))

    def test_offline_fallback_view(self):
        """Offline fallback page renders successfully."""
        res = self.client.get(reverse("sync:pwa_offline"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Sem conexão com a internet")

    def test_offline_bootstrap_data_view(self):
        """Bootstrap view returns vehicles, fuel types, categories and templates for offline caching."""
        res = self.client.get(reverse("sync:sync_bootstrap"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["vehicles"]), 1)
        self.assertEqual(data["vehicles"][0]["name"], "Carro PWA")
        self.assertTrue(any(c["slug"] == "estacionamento" for c in data["categories"]))
        self.assertTrue(any(s["name"] == "Troca de Óleo" for s in data["service_types"]))

    def test_sync_fuel_record(self):
        """Syncing a fuel record creates Refueling and updates vehicle odometer."""
        records = [
            {
                "id": "rec-fuel-01",
                "entity_type": "fuel",
                "created_offline_at": timezone.now().isoformat(),
                "payload": {
                    "vehicle": str(self.vehicle.id),
                    "occurred_at": "2026-09-29",
                    "station_name": "Posto Ipiranga",
                    "odometer": 10500,
                    "liters": "40.00",
                    "total_amount": "240.00",
                    "price_per_liter": "6.00",
                    "is_full_tank": True,
                },
            }
        ]

        res = self.client.post(
            reverse("sync:sync_records"),
            data=json.dumps({"records": records}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertEqual(result["synced"], 1)
        self.assertEqual(result["failed"], 0)

        # Verify DB
        refuel = Refueling.objects.filter(vehicle=self.vehicle).first()
        self.assertIsNotNone(refuel)
        self.assertEqual(refuel.odometer, 10500)
        self.assertEqual(refuel.total_amount, Decimal("240.00"))

        # Vehicle odometer cache updated
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_odometer_cache, 10500)

    def test_sync_expense_record(self):
        """Syncing an expense record creates Expense."""
        records = [
            {
                "id": "rec-exp-01",
                "entity_type": "expense",
                "created_offline_at": timezone.now().isoformat(),
                "payload": {
                    "vehicle": str(self.vehicle.id),
                    "category": str(self.category.id),
                    "occurred_at": "2026-09-29",
                    "amount": "45.00",
                    "description": "Estacionamento Shopping",
                    "odometer": 10520,
                },
            }
        ]

        res = self.client.post(
            reverse("sync:sync_records"),
            data=json.dumps({"records": records}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["synced"], 1)

        exp = Expense.objects.filter(vehicle=self.vehicle).first()
        self.assertIsNotNone(exp)
        self.assertEqual(exp.amount, Decimal("45.00"))
        self.assertEqual(exp.description, "Estacionamento Shopping")

    def test_sync_maintenance_record(self):
        """Syncing a maintenance record creates Maintenance."""
        records = [
            {
                "id": "rec-maint-01",
                "entity_type": "maintenance",
                "created_offline_at": timezone.now().isoformat(),
                "payload": {
                    "vehicle": str(self.vehicle.id),
                    "service_type": str(self.service_type.id),
                    "occurred_at": "2026-09-29",
                    "odometer": 11000,
                    "total_amount": "350.00",
                    "maintenance_type": "preventive",
                    "workshop_name": "Oficina Central",
                    "description": "Revisão e óleo",
                },
            }
        ]

        res = self.client.post(
            reverse("sync:sync_records"),
            data=json.dumps({"records": records}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["synced"], 1)

        maint = Maintenance.objects.filter(vehicle=self.vehicle).first()
        self.assertIsNotNone(maint)
        self.assertEqual(maint.total_amount, Decimal("350.00"))

    def test_sync_checklist_record(self):
        """Syncing a checklist record creates ChecklistInspection and items."""
        records = [
            {
                "id": "rec-check-01",
                "entity_type": "checklist",
                "created_offline_at": timezone.now().isoformat(),
                "payload": {
                    "vehicle": str(self.vehicle.id),
                    "template": str(self.template.id),
                    "title": "Checagem Semanal Offline",
                    "odometer": 11050,
                    "items": [
                        {
                            "title": "Nível de Óleo",
                            "category": "Fluidos",
                            "status": "ok",
                            "notes": "Tudo ok",
                        }
                    ],
                },
            }
        ]

        res = self.client.post(
            reverse("sync:sync_records"),
            data=json.dumps({"records": records}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["synced"], 1)

        inspection = ChecklistInspection.objects.filter(vehicle=self.vehicle).first()
        self.assertIsNotNone(inspection)
        self.assertEqual(inspection.title, "Checagem Semanal Offline")
        self.assertEqual(inspection.items.count(), 1)

    def test_sync_record_non_owned_vehicle_fails_gracefully(self):
        """Attempting to sync a record for a vehicle not owned by user records an error."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpassword123",
        )
        other_vehicle = Vehicle.objects.create(
            owner_primary=other_user,
            name="Outro Carro",
            year=2021,
            initial_odometer=5000,
        )

        records = [
            {
                "id": "rec-hacker-01",
                "entity_type": "fuel",
                "payload": {
                    "vehicle": str(other_vehicle.id),
                    "occurred_at": "2026-09-29",
                    "odometer": 6000,
                    "liters": "30",
                    "total_amount": "150",
                },
            }
        ]

        res = self.client.post(
            reverse("sync:sync_records"),
            data=json.dumps({"records": records}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertEqual(result["synced"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["results"][0]["status"], "error")
