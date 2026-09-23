"""
Tests for the dashboard app, including CSV export functionality.
"""
import csv
import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.dashboard.selectors import DashboardSelectors
from apps.expenses.models import Expense, ExpenseCategory
from apps.fuel.models import FuelType, Refueling
from apps.vehicles.models import Vehicle

User = get_user_model()


class CSVExportTests(TestCase):
    """Tests for CSV export functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="export@example.com",
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
        self.fuel_type = FuelType.objects.create(
            name="Gasolina",
            code="gasoline",
            is_system=True,
        )
        self.category = ExpenseCategory.objects.create(
            name="Estacionamento",
            slug="estacionamento",
            is_system=True,
        )
        self.client.login(email=self.user.email, password="testpass123")

    def test_export_refuelings_csv_requires_login(self):
        """Test that CSV export requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("dashboard:export_refuelings_csv"))
        self.assertEqual(response.status_code, 302)

    def test_export_refuelings_csv(self):
        """Test exporting refuelings to CSV."""
        Refueling.objects.create(
            vehicle=self.vehicle,
            occurred_at="2026-01-15",
            odometer=10500,
            liters=40.000,
            total_amount=200.00,
            fuel_type=self.fuel_type,
            is_full_tank=True,
        )
        response = self.client.get(reverse("dashboard:export_refuelings_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])

        # Decode content (strip BOM)
        content = response.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content), delimiter=";")
        rows = list(reader)
        # Header + 1 data row
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "vehicle")
        self.assertEqual(rows[1][0], "Meu Carro")
        self.assertEqual(rows[1][2], "2026-01-15")

    def test_export_expenses_csv(self):
        """Test exporting expenses to CSV."""
        Expense.objects.create(
            vehicle=self.vehicle,
            category=self.category,
            occurred_at="2026-01-15",
            amount=50.00,
            description="Estacionamento shopping",
        )
        response = self.client.get(reverse("dashboard:export_expenses_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])

        content = response.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content), delimiter=";")
        rows = list(reader)
        # Header + 1 data row
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "vehicle")
        self.assertEqual(rows[1][0], "Meu Carro")
        self.assertEqual(rows[1][2], "Estacionamento shopping")

    def test_export_refuelings_csv_empty(self):
        """Test exporting refuelings to CSV when there are no records."""
        response = self.client.get(reverse("dashboard:export_refuelings_csv"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content), delimiter=";")
        rows = list(reader)
        # Only header row
        self.assertEqual(len(rows), 1)

    def test_export_expenses_csv_empty(self):
        """Test exporting expenses to CSV when there are no records."""
        response = self.client.get(reverse("dashboard:export_expenses_csv"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content), delimiter=";")
        rows = list(reader)
        # Only header row
        self.assertEqual(len(rows), 1)


class DashboardViewTests(TestCase):
    """Tests for dashboard views."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="dash@example.com",
            password="testpass123",
        )
        self.client.login(email=self.user.email, password="testpass123")

    def test_dashboard_home_requires_login(self):
        """Test that the dashboard requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_home_renders(self):
        """Test that the dashboard home renders."""
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")

    def test_dashboard_home_renders_with_vehicle_switcher(self):
        """Dashboard home renders the vehicle switcher without URL errors."""
        first = Vehicle.objects.create(
            owner_primary=self.user,
            name="Carro A",
            brand="Fiat",
            model="Uno",
            year=2015,
            initial_odometer=1000,
        )
        second = Vehicle.objects.create(
            owner_primary=self.user,
            name="Carro B",
            brand="Volkswagen",
            model="Gol",
            year=2018,
            initial_odometer=5000,
        )
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")
        self.assertContains(
            response, reverse("dashboard:set_active_vehicle", args=[first.id])
        )
        self.assertContains(
            response, reverse("dashboard:set_active_vehicle", args=[second.id])
        )

    def test_expense_categories_breakdown_returns_json_safe_totals(self):
        """Category breakdown data must render as valid JS (no Decimal repr)."""
        vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Meu Carro",
            brand="Fiat",
            model="Uno",
            year=2015,
            initial_odometer=1000,
        )
        category = ExpenseCategory.objects.create(
            name="Estacionamento",
            slug="estacionamento",
            is_system=True,
        )
        Expense.objects.create(
            vehicle=vehicle,
            category=category,
            occurred_at="2026-01-15",
            amount=Decimal("50.00"),
        )
        breakdown = DashboardSelectors.get_expense_categories_breakdown(
            self.user, vehicle=vehicle
        )
        self.assertEqual(len(breakdown), 1)
        self.assertIsInstance(breakdown[0]["total"], float)
        self.assertIsInstance(breakdown[0]["percentage"], float)

        # The template renders the list with |safe; a Decimal repr would
        # produce invalid JavaScript (ReferenceError: Decimal is not defined).
        from django.template import Context, Template

        rendered = Template("{{ data|safe }}").render(Context({"data": breakdown}))
        self.assertNotIn("Decimal(", rendered)
