"""
Tests for the imports app: Drivvo CSV parser, import service and views.
"""
import os
import tempfile
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.expenses.models import Expense
from apps.fuel.models import FuelType, Refueling
from apps.vehicles.models import Vehicle

from .drivvo_parser import (
    DrivvoParser,
    detect_delimiter,
    detect_encoding,
    extract_expenses,
    extract_refuelings,
    extract_vehicles,
    map_expense_category,
    map_fuel_type,
    map_vehicle_type,
    parse_date,
    parse_decimal,
    parse_drivvo_csv,
    parse_sections,
    parse_year,
)
from .services import import_drivvo_data

User = get_user_model()

SAMPLE_PATH = Path(__file__).resolve().parent / "samples" / "drivvo_sample.csv"

# A minimal Drivvo-style file using the plain (non-#) section markers and ";"
# delimiter, mirroring older exports.
SEMICOLON_CSV = (
    "Veículo;\n"
    "Nome do veículo;Placa;Ano;Marca;Modelo\n"
    "Meu Carro;ABC1234;2020;Toyota;Corolla\n"
    "Abastecimento;\n"
    "Nome do veículo;Odômetro (km);Data;Combustível;Valor total;Volume\n"
    "Meu Carro;10500;15/01/2026 10:30;Gasolina;200.00;40.000\n"
    "Despesa;\n"
    "Nome do veículo;Data;Valor total;Tipo de despesa\n"
    "Meu Carro;16/01/2026 11:00;50.00;Estacionamento\n"
    "Serviço;\n"
    "Nome do veículo;Data;Tipo de serviço\n"
    "Meu Carro;17/01/2026 12:00;Troca de óleo\n"
)


def _write_temp(content, encoding="utf-8-sig"):
    """Write ``content`` to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding=encoding) as f:
        f.write(content)
    return path


class DrivvoParserTests(SimpleTestCase):
    """Tests for the Drivvo CSV parser."""

    def test_detect_encoding_sample_file(self):
        """The real Drivvo export is encoded in cp1252."""
        self.assertEqual(detect_encoding(str(SAMPLE_PATH)), "cp1252")

    def test_detect_delimiter(self):
        """Comma delimiter is detected for quoted fields."""
        lines = ['"a","b"', '"1","2"']
        self.assertEqual(detect_delimiter(lines), ",")

    def test_parse_sections_on_sample_file(self):
        """The sample file sections are identified with correct row counts."""
        sections = parse_sections(str(SAMPLE_PATH))
        self.assertEqual(len(sections["vehicles"]["rows"]), 1)
        self.assertEqual(len(sections["refuelings"]["rows"]), 3)
        self.assertEqual(len(sections["expenses"]["rows"]), 2)
        self.assertEqual(
            sections["unsupported_sections"],
            ["Lembrete", "Percurso", "Receita", "Serviço"],
        )

    def test_parse_sections_cleans_duplicate_headers(self):
        """
        Multi-fuel exports repeat headers (Preço / gal, Valor total, Volume).
        The first occurrence (primary fuel) must win.
        """
        sections = parse_sections(str(SAMPLE_PATH))
        first = sections["refuelings"]["rows"][0]
        self.assertEqual(first["Preço / gal"], "3.17")
        self.assertEqual(first["Valor total"], "50")
        self.assertEqual(first["Volume"], "15.773")

    def test_parse_sections_semicolon_format(self):
        """Plain section markers with ';' delimiter are also supported."""
        path = _write_temp(SEMICOLON_CSV, encoding="utf-8-sig")
        try:
            sections = parse_sections(path)
            self.assertEqual(len(sections["vehicles"]["rows"]), 1)
            self.assertEqual(len(sections["refuelings"]["rows"]), 1)
            self.assertEqual(len(sections["expenses"]["rows"]), 1)
            self.assertEqual(sections["unsupported_sections"], ["Serviço"])
            row = sections["refuelings"]["rows"][0]
            self.assertEqual(row["Nome do veículo"], "Meu Carro")
            self.assertEqual(row["Valor total"], "200.00")
        finally:
            os.remove(path)

    def test_parse_sections_empty_file(self):
        """An empty file yields empty sections and no unsupported ones."""
        path = _write_temp("")
        try:
            sections = parse_sections(path)
            self.assertEqual(sections["vehicles"]["rows"], [])
            self.assertEqual(sections["refuelings"]["rows"], [])
            self.assertEqual(sections["expenses"]["rows"], [])
            self.assertEqual(sections["unsupported_sections"], [])
        finally:
            os.remove(path)

    def test_extract_vehicles(self):
        """Vehicle extraction maps the Drivvo columns correctly."""
        sections = parse_sections(str(SAMPLE_PATH))
        vehicles = extract_vehicles(sections)
        self.assertEqual(len(vehicles), 1)
        vehicle = vehicles[0]
        self.assertEqual(vehicle["name"], "Citroen C3 XTR")
        self.assertTrue(vehicle["is_active"])
        self.assertEqual(vehicle["vehicle_type"], "car")
        self.assertEqual(vehicle["brand"], "Citroën")
        self.assertEqual(vehicle["model"], "C3 XTR")
        self.assertEqual(vehicle["plate"], "EJK5495")
        self.assertEqual(vehicle["year"], 2009)

    def test_extract_refuelings(self):
        """Refueling extraction parses dates, decimals and booleans."""
        sections = parse_sections(str(SAMPLE_PATH))
        refuelings = extract_refuelings(sections)
        self.assertEqual(len(refuelings), 3)
        first = refuelings[0]
        self.assertEqual(first["vehicle_name"], "Citroen C3 XTR")
        self.assertEqual(first["odometer"], Decimal("95729"))
        self.assertEqual(first["occurred_at"].isoformat(), "2026-08-12")
        self.assertEqual(first["fuel_type_name"], "Etanol")
        self.assertEqual(first["price_per_liter"], Decimal("3.17"))
        self.assertEqual(first["total_amount"], Decimal("50"))
        self.assertEqual(first["liters"], Decimal("15.773"))
        self.assertFalse(first["is_full_tank"])
        self.assertEqual(first["station_name"], "Rede VP1000, Régis Bittencourt.")

    def test_extract_expenses(self):
        """Expense extraction maps values and joins Motivo + Observação."""
        sections = parse_sections(str(SAMPLE_PATH))
        expenses = extract_expenses(sections)
        self.assertEqual(len(expenses), 2)
        first = expenses[0]
        self.assertEqual(first["vehicle_name"], "Citroen C3 XTR")
        self.assertEqual(first["occurred_at"].isoformat(), "2024-05-22")
        self.assertEqual(first["amount"], Decimal("22.8"))
        self.assertEqual(first["category_name"], "Conveniência Posto")
        self.assertEqual(
            first["vendor_name"], "Carrefour Comercio E Industria Ltda"
        )
        self.assertEqual(first["notes"], "Pessoal - Bardhal flex")

    def test_parse_decimal(self):
        """parse_decimal handles both Brazilian and Drivvo number formats."""
        self.assertEqual(parse_decimal("22.8"), Decimal("22.8"))
        self.assertEqual(parse_decimal("3.17"), Decimal("3.17"))
        self.assertEqual(parse_decimal("1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_decimal("1,234.56"), Decimal("1234.56"))
        self.assertEqual(parse_decimal("1.000"), Decimal("1.000"))
        self.assertEqual(parse_decimal("R$ 12,50"), Decimal("12.50"))
        self.assertIsNone(parse_decimal(""))
        self.assertIsNone(parse_decimal("Quilômetros (km)"))
        self.assertIsNone(parse_decimal(None))

    def test_parse_date(self):
        """parse_date supports the Drivvo DD/MM/YYYY HH:MM format."""
        parsed = parse_date("12/08/2026 17:00")
        self.assertEqual(parsed.isoformat(), "2026-08-12")
        self.assertEqual(parse_date("21/11/2023").isoformat(), "2023-11-21")
        self.assertIsNone(parse_date("not a date"))
        self.assertIsNone(parse_date(None))

    def test_parse_year(self):
        self.assertEqual(parse_year("2009"), 2009)
        self.assertEqual(parse_year(2009), 2009)
        self.assertIsNone(parse_year(""))
        self.assertIsNone(parse_year(None))

    def test_mappings(self):
        self.assertEqual(map_vehicle_type("Carro"), "car")
        self.assertEqual(map_vehicle_type("Moto"), "motorcycle")
        self.assertEqual(map_vehicle_type("Desconhecido"), "car")
        self.assertEqual(map_fuel_type("Etanol"), "Etanol")
        self.assertEqual(map_fuel_type("Gasolina Comum"), "Gasolina comum")
        self.assertEqual(map_expense_category("Conveniência Posto"), "Conveniência")
        self.assertEqual(map_expense_category("Desconhecido"), "Outros")

    def test_legacy_parser_api(self):
        """DrivvoParser.parse and parse_drivvo_csv still work."""
        result = parse_drivvo_csv(str(SAMPLE_PATH))
        self.assertEqual(len(result["vehicles"]), 1)
        self.assertEqual(len(result["refuelings"]), 3)
        self.assertEqual(len(result["expenses"]), 2)
        self.assertIn("Serviço", result["unsupported_sections"])

        parser = DrivvoParser()
        self.assertEqual(len(parser.parse(str(SAMPLE_PATH))["refuelings"]), 3)


class DrivvoImportServiceTests(TestCase):
    """Tests for the Drivvo import service."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="import@example.com",
            password="testpass123",
        )
        self.parsed_data = self._parse_sample()

    @staticmethod
    def _parse_sample():
        sections = parse_sections(str(SAMPLE_PATH))
        return {
            "vehicles": extract_vehicles(sections),
            "refuelings": extract_refuelings(sections),
            "expenses": extract_expenses(sections),
            "unsupported_sections": sections.get("unsupported_sections", []),
        }

    def test_import_creates_vehicle_refuelings_and_expenses(self):
        """Importing the sample file creates all supported records."""
        result = import_drivvo_data(self.user, self.parsed_data)

        self.assertEqual(result["vehicles_created"], 1)
        self.assertEqual(result["vehicles_updated"], 0)
        self.assertEqual(result["refuelings_created"], 3)
        self.assertEqual(result["expenses_created"], 2)
        self.assertEqual(result["refuelings_skipped"], 0)
        self.assertEqual(result["expenses_skipped"], 0)

        vehicle = Vehicle.objects.get(owner_primary=self.user)
        self.assertEqual(vehicle.name, "Citroen C3 XTR")
        self.assertEqual(vehicle.plate, "EJK5495")
        self.assertEqual(vehicle.brand, "Citroën")
        self.assertEqual(vehicle.model, "C3 XTR")
        self.assertEqual(vehicle.year, 2009)

        self.assertEqual(vehicle.refuelings.count(), 3)
        first = vehicle.refuelings.get(occurred_at="2026-08-12")
        self.assertEqual(first.odometer, 95729)
        self.assertEqual(first.liters, Decimal("15.773"))
        self.assertEqual(first.total_amount, Decimal("50.00"))
        self.assertEqual(float(first.price_per_liter), 3.17)
        self.assertEqual(first.fuel_type.name, "Etanol")
        self.assertEqual(first.station_name, "Rede VP1000, Régis Bittencourt.")

        self.assertEqual(vehicle.expenses.count(), 2)
        first_expense = vehicle.expenses.get(occurred_at="2024-05-22")
        self.assertEqual(first_expense.amount, Decimal("22.80"))
        self.assertEqual(first_expense.category.name, "Conveniência")
        self.assertEqual(first_expense.odometer, 85127)

        # Vehicle odometer cache updated from the refuelings.
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.current_odometer_cache, 95729)

    def test_import_is_idempotent(self):
        """Re-importing the same Drivvo file must not duplicate records."""
        first_result = import_drivvo_data(self.user, self.parsed_data)
        self.assertEqual(first_result["refuelings_created"], 3)
        self.assertEqual(first_result["expenses_created"], 2)

        second_result = import_drivvo_data(self.user, self.parsed_data)

        self.assertEqual(second_result["vehicles_created"], 0)
        self.assertEqual(second_result["vehicles_updated"], 1)
        self.assertEqual(second_result["refuelings_created"], 0)
        self.assertEqual(second_result["expenses_created"], 0)
        self.assertEqual(second_result["refuelings_skipped"], 3)
        self.assertEqual(second_result["expenses_skipped"], 2)

        vehicle = Vehicle.objects.get(owner_primary=self.user)
        self.assertEqual(vehicle.refuelings.count(), 3)
        self.assertEqual(vehicle.expenses.count(), 2)

    def test_dedupe_imports_command_removes_duplicates(self):
        """dedupe_imports removes duplicate records keeping the oldest copy."""
        from io import StringIO

        from django.core.management import call_command

        import_drivvo_data(self.user, self.parsed_data)
        vehicle = Vehicle.objects.get(owner_primary=self.user)

        # Create exact copies as a pre-fix double import would have left behind.
        refueling = vehicle.refuelings.first()
        Refueling.objects.create(
            vehicle=refueling.vehicle,
            occurred_at=refueling.occurred_at,
            odometer=refueling.odometer,
            liters=refueling.liters,
            total_amount=refueling.total_amount,
            price_per_liter=refueling.price_per_liter,
            fuel_type=refueling.fuel_type,
            is_full_tank=refueling.is_full_tank,
            station_name=refueling.station_name,
            notes=refueling.notes,
        )
        expense = vehicle.expenses.first()
        Expense.objects.create(
            vehicle=expense.vehicle,
            occurred_at=expense.occurred_at,
            amount=expense.amount,
            category=expense.category,
            odometer=expense.odometer,
            vendor_name=expense.vendor_name,
            notes=expense.notes,
        )

        self.assertEqual(vehicle.refuelings.count(), 4)
        self.assertEqual(vehicle.expenses.count(), 3)

        # Dry run must not delete anything.
        call_command("dedupe_imports", stdout=StringIO())
        self.assertEqual(vehicle.refuelings.count(), 4)
        self.assertEqual(vehicle.expenses.count(), 3)

        # --apply removes the duplicates.
        call_command("dedupe_imports", "--apply", stdout=StringIO())
        self.assertEqual(vehicle.refuelings.count(), 3)
        self.assertEqual(vehicle.expenses.count(), 2)

    def test_import_reports_unsupported_sections(self):
        """Unsupported sections present in the file are reported as warnings."""
        result = import_drivvo_data(self.user, self.parsed_data)
        self.assertTrue(
            any("Serviço" in warning for warning in result["warnings"])
        )
        self.assertTrue(
            any("não importadas" in warning for warning in result["warnings"])
        )

    def test_import_updates_existing_vehicle_by_plate(self):
        """A vehicle matching the CSV plate is updated instead of recreated."""
        existing = Vehicle.objects.create(
            owner_primary=self.user,
            name="Antigo",
            brand="",
            model="",
            year=2000,
            plate="EJK5495",
        )
        result = import_drivvo_data(self.user, self.parsed_data)
        self.assertEqual(result["vehicles_created"], 0)
        self.assertEqual(result["vehicles_updated"], 1)

        existing.refresh_from_db()
        self.assertEqual(existing.name, "Antigo")  # name is kept when already set
        self.assertEqual(existing.brand, "Citroën")
        self.assertEqual(existing.model, "C3 XTR")
        self.assertEqual(existing.year, 2009)
        # The refuelings still point to the same vehicle.
        self.assertEqual(existing.refuelings.count(), 3)

    def test_import_creates_fuel_type_when_missing(self):
        """A fuel type not in the system is created for the user."""
        self.parsed_data["refuelings"][0]["fuel_type_name"] = "Hidrogênio"
        result = import_drivvo_data(self.user, self.parsed_data)
        self.assertEqual(result["refuelings_created"], 3)
        fuel_type = FuelType.objects.get(user=self.user, name="Hidrogênio")
        self.assertIsNotNone(fuel_type)

    def test_import_skips_refueling_for_unknown_vehicle(self):
        """Refuelings referencing a vehicle not in the file are skipped."""
        data = {
            "vehicles": [],
            "refuelings": [
                {
                    "vehicle_name": "Fantasma",
                    "odometer": 100,
                    "occurred_at": parse_date("01/01/2026 10:00"),
                    "fuel_type_name": "Etanol",
                    "price_per_liter": Decimal("3.50"),
                    "total_amount": Decimal("35.00"),
                    "liters": Decimal("10.000"),
                }
            ],
            "expenses": [],
            "unsupported_sections": [],
        }
        result = import_drivvo_data(self.user, data)
        self.assertEqual(result["refuelings_skipped"], 1)
        self.assertEqual(Refueling.objects.count(), 0)
        self.assertTrue(result["warnings"])

    def test_import_skips_invalid_refueling(self):
        """Refuelings without liters and total/price are skipped with errors."""
        data = {
            "vehicles": [
                {
                    "name": "Meu Carro",
                    "brand": "Toyota",
                    "model": "Corolla",
                    "year": 2020,
                    "plate": "ABC1234",
                    "is_active": True,
                    "odometer": 1000,
                    "vehicle_type": "car",
                }
            ],
            "refuelings": [
                {
                    "vehicle_name": "Meu Carro",
                    "odometer": 1000,
                    "occurred_at": parse_date("01/01/2026 10:00"),
                    "fuel_type_name": "Etanol",
                    "price_per_liter": None,
                    "total_amount": None,
                    "liters": None,
                }
            ],
            "expenses": [],
            "unsupported_sections": [],
        }
        result = import_drivvo_data(self.user, data)
        self.assertEqual(result["refuelings_skipped"], 1)
        self.assertEqual(Refueling.objects.count(), 0)
        self.assertTrue(result["errors"])

    def test_import_skips_expense_without_amount(self):
        """Expenses without a valid amount are skipped with errors."""
        data = {
            "vehicles": [
                {
                    "name": "Meu Carro",
                    "brand": "Toyota",
                    "model": "Corolla",
                    "year": 2020,
                    "plate": "ABC1234",
                    "is_active": True,
                    "odometer": 1000,
                    "vehicle_type": "car",
                }
            ],
            "refuelings": [],
            "expenses": [
                {
                    "vehicle_name": "Meu Carro",
                    "odometer": None,
                    "occurred_at": parse_date("01/01/2026 10:00"),
                    "amount": None,
                    "category_name": "Seguro",
                    "vendor_name": "",
                    "notes": "",
                }
            ],
            "unsupported_sections": [],
        }
        result = import_drivvo_data(self.user, data)
        self.assertEqual(result["expenses_skipped"], 1)
        self.assertEqual(Expense.objects.count(), 0)
        self.assertTrue(result["errors"])


class DrivvoImportViewTests(TestCase):
    """Tests for the Drivvo import view."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="view@example.com",
            password="testpass123",
        )
        self.client.login(email=self.user.email, password="testpass123")

    @staticmethod
    def _sample_upload(name="drivvo.csv"):
        with open(SAMPLE_PATH, "rb") as f:
            content = f.read()
        return SimpleUploadedFile(name, content, content_type="text/csv")

    def test_import_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("imports:import_drivvo"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_import_page_renders(self):
        response = self.client.get(reverse("imports:import_drivvo"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "imports/import_drivvo.html")

    def test_post_imports_csv(self):
        response = self.client.post(
            reverse("imports:import_drivvo"),
            {"csv_file": self._sample_upload()},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:home"))
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertEqual(Refueling.objects.count(), 3)
        self.assertEqual(Expense.objects.count(), 2)

    def test_post_rejects_non_csv(self):
        from django.contrib.messages import get_messages

        upload = SimpleUploadedFile(
            "dados.txt", b"conteudo", content_type="text/plain"
        )
        response = self.client.post(
            reverse("imports:import_drivvo"),
            {"csv_file": upload},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("imports:import_drivvo"))
        self.assertEqual(Vehicle.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("CSV" in str(message) for message in messages))

    def test_post_without_file_reports_error(self):
        response = self.client.post(reverse("imports:import_drivvo"), {})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("imports:import_drivvo"))
        self.assertEqual(Vehicle.objects.count(), 0)
