"""
Tests for the checklists app.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.vehicles.models import Vehicle

from .models import (
    ChecklistInspection,
    ChecklistInspectionItem,
    ChecklistTemplate,
    ChecklistTemplateItem,
    InspectionStatus,
    ItemStatus,
)

User = get_user_model()


class ChecklistModelTests(TestCase):
    """Unit tests for Checklist models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="checklist_user@example.com",
            password="testpassword123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="SUV Familiar",
            year=2021,
            initial_odometer=20000,
            current_odometer_cache=20000,
        )
        self.template = ChecklistTemplate.objects.create(
            name="Inspeção Rápida",
            is_system=True,
        )
        self.item1 = ChecklistTemplateItem.objects.create(
            template=self.template,
            category="Fluidos",
            title="Nível de Óleo",
            order=1,
        )
        self.item2 = ChecklistTemplateItem.objects.create(
            template=self.template,
            category="Pneus",
            title="Calibragem",
            order=2,
        )

    def test_inspection_status_evaluation(self):
        """Inspection status evaluates to APPROVED when all items are OK."""
        inspection = ChecklistInspection.objects.create(
            vehicle=self.vehicle,
            template=self.template,
            title="Checkup Pré-Viagem",
            odometer=20500,
        )
        ChecklistInspectionItem.objects.create(
            inspection=inspection,
            category=self.item1.category,
            title=self.item1.title,
            status=ItemStatus.OK,
        )
        ChecklistInspectionItem.objects.create(
            inspection=inspection,
            category=self.item2.category,
            title=self.item2.title,
            status=ItemStatus.OK,
        )
        inspection.evaluate_status()
        self.assertEqual(inspection.status, InspectionStatus.APPROVED)

        # Vehicle odometer cache updated
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_odometer_cache, 20500)

    def test_inspection_status_evaluation_with_warning_and_problem(self):
        """WARNING if attention item exists; REJECTED if problem item exists."""
        inspection = ChecklistInspection.objects.create(
            vehicle=self.vehicle,
            template=self.template,
            title="Checkup",
        )
        item1 = ChecklistInspectionItem.objects.create(
            inspection=inspection,
            category="Fluidos",
            title="Óleo",
            status=ItemStatus.ATTENTION,
        )
        inspection.evaluate_status()
        self.assertEqual(inspection.status, InspectionStatus.WARNING)

        # Add a problem item
        ChecklistInspectionItem.objects.create(
            inspection=inspection,
            category="Freios",
            title="Pastilha gasta",
            status=ItemStatus.PROBLEM,
        )
        inspection.evaluate_status()
        self.assertEqual(inspection.status, InspectionStatus.REJECTED)


class ChecklistViewTests(TestCase):
    """View tests for Checklists."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="checklist_view@example.com",
            password="testpassword123",
        )
        self.vehicle = Vehicle.objects.create(
            owner_primary=self.user,
            name="Hatch",
            year=2021,
            initial_odometer=30000,
            current_odometer_cache=30000,
        )
        self.template = ChecklistTemplate.objects.create(
            name="Revisão Padrão",
            is_system=True,
        )
        self.item1 = ChecklistTemplateItem.objects.create(
            template=self.template,
            category="Luzes",
            title="Farol Dianteiro",
            order=1,
        )
        self.client.login(email=self.user.email, password="testpassword123")

    def test_checklist_list_and_create(self):
        """Test listing checklists and submitting an inspection form."""
        list_url = reverse("checklists:list")
        res = self.client.get(list_url)
        self.assertEqual(res.status_code, 200)

        create_url = reverse("checklists:create")
        res_form = self.client.get(create_url)
        self.assertEqual(res_form.status_code, 200)

        post_data = {
            "vehicle": str(self.vehicle.id),
            "template": str(self.template.id),
            "title": "Inspeção Mensal",
            "odometer": 30500,
            "checked_at": "2026-09-22T10:00",
            "notes": "Tudo ok",
            f"item_status_{self.item1.id}": "ok",
            f"item_notes_{self.item1.id}": "Perfeito estado",
        }
        res_post = self.client.post(create_url, post_data)
        self.assertEqual(res_post.status_code, 302)

        self.assertEqual(ChecklistInspection.objects.count(), 1)
        ins = ChecklistInspection.objects.first()
        self.assertEqual(ins.status, InspectionStatus.APPROVED)
        self.assertEqual(ins.items.count(), 1)
        self.assertEqual(ins.items.first().notes, "Perfeito estado")

