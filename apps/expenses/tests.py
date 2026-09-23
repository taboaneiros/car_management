"""
Tests for the expenses app.
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.vehicles.models import Vehicle

from .models import CategoryKind, Expense, ExpenseCategory

User = get_user_model()


class ExpenseModelTests(TestCase):
    """Tests for expense models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="expense@example.com",
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
        self.category = ExpenseCategory.objects.create(
            user=self.user,
            name="Estacionamento",
            slug="estacionamento",
            kind=CategoryKind.VARIABLE,
        )

    def test_create_expense(self):
        """Test creating an expense record."""
        expense = Expense.objects.create(
            vehicle=self.vehicle,
            category=self.category,
            occurred_at="2026-01-15",
            amount=50.00,
            description="Estacionamento shopping",
        )
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(expense.vehicle, self.vehicle)
        self.assertEqual(expense.category, self.category)
        self.assertEqual(expense.amount, 50.00)

    def test_expense_accepts_pdf_attachment(self):
        """Test that a PDF attachment can be uploaded to an expense."""
        pdf_content = b"%PDF-1.4 test pdf content"
        attachment = SimpleUploadedFile(
            "nota.pdf",
            pdf_content,
            content_type="application/pdf",
        )
        expense = Expense.objects.create(
            vehicle=self.vehicle,
            category=self.category,
            occurred_at="2026-01-15",
            amount=50.00,
            attachment=attachment,
        )
        self.assertTrue(expense.attachment)
        self.assertTrue(expense.attachment.name.endswith(".pdf"))

    def test_expense_accepts_image_attachment(self):
        """Test that an image attachment can be uploaded to an expense."""
        image_content = b"\x89PNG\r\n\x1a\n fake image content"
        attachment = SimpleUploadedFile(
            "foto.png",
            image_content,
            content_type="image/png",
        )
        expense = Expense.objects.create(
            vehicle=self.vehicle,
            occurred_at="2026-01-15",
            amount=50.00,
            attachment=attachment,
        )
        self.assertTrue(expense.attachment)
        self.assertTrue(expense.attachment.name.endswith(".png"))


class ExpenseCategorySystemRecordTests(TestCase):
    """Tests for system expense categories being available to all users."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="expensecat@example.com",
            password="testpass123",
        )

    def test_system_categories_exist(self):
        """Test that system expense categories are created by data migration."""
        system_categories = ExpenseCategory.objects.filter(is_system=True)
        self.assertGreaterEqual(system_categories.count(), 1)

    def test_system_categories_available_to_user(self):
        """Test that system categories (user=None) are visible to a user."""
        system_categories = ExpenseCategory.objects.filter(
            is_active=True,
            user__isnull=True,
        )
        self.assertGreaterEqual(system_categories.count(), 1)

    def test_user_can_create_own_category(self):
        """Test that a user can create their own expense category."""
        category = ExpenseCategory.objects.create(
            user=self.user,
            name="Categoria Personalizada",
            slug="categoria-personalizada",
        )
        self.assertEqual(category.user, self.user)
        self.assertFalse(category.is_system)


class ExpenseViewTests(TestCase):
    """Tests for expense views."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="expenseview@example.com",
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

    def test_expense_list_requires_login(self):
        """Test that the expense list requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("expenses:list"))
        self.assertEqual(response.status_code, 302)

    def test_expense_list_renders(self):
        """Test that the expense list renders for an authenticated user."""
        response = self.client.get(reverse("expenses:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "expenses/expense_list.html")

    def test_expense_create_renders(self):
        """Test that the expense create form renders."""
        response = self.client.get(reverse("expenses:create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "expenses/expense_form.html")

    def test_expense_create_with_pdf(self):
        """Test creating an expense with a PDF attachment via the form."""
        pdf_content = b"%PDF-1.4 test pdf content"
        attachment = SimpleUploadedFile(
            "nota.pdf",
            pdf_content,
            content_type="application/pdf",
        )
        response = self.client.post(
            reverse("expenses:create"),
            {
                "vehicle": self.vehicle.id,
                "occurred_at": "2026-01-15",
                "amount": "50.00",
                "description": "Estacionamento",
                "attachment": attachment,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Expense.objects.count(), 1)
        expense = Expense.objects.first()
        self.assertTrue(expense.attachment)
        self.assertTrue(expense.attachment.name.endswith(".pdf"))

    def test_category_list_renders(self):
        """Test that the category list renders."""
        response = self.client.get(reverse("expenses:category_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "expenses/category_list.html")

    def test_category_create_renders(self):
        """Test that the category create form renders."""
        response = self.client.get(reverse("expenses:category_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "expenses/category_form.html")

    def test_category_create(self):
        """Test creating a category via the form."""
        response = self.client.post(
            reverse("expenses:category_create"),
            {
                "name": "Pedágio",
                "kind": CategoryKind.VARIABLE,
            },
        )
        self.assertEqual(response.status_code, 302)
        # Only the user's own category should be created (system categories
        # also exist from the data migration).
        category = ExpenseCategory.objects.get(user=self.user, slug="pedagio")
        self.assertEqual(category.user, self.user)
        self.assertEqual(category.slug, "pedagio")

