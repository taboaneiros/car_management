import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.vehicles.models import Vehicle


class ItemStatus(models.TextChoices):
    """Evaluation status of an individual checklist item."""
    OK = "ok", "Conforme / OK"
    ATTENTION = "attention", "Atenção / Ressalva"
    PROBLEM = "problem", "Não Conforme / Problema"
    NA = "na", "Não se aplica"


class InspectionStatus(models.TextChoices):
    """Overall status of a completed checklist inspection."""
    APPROVED = "approved", "Aprovado"
    PENDING = "pending", "Pendente"
    WARNING = "warning", "Atenção (com ressalvas)"
    REJECTED = "rejected", "Reprovado (não conforme)"


class ChecklistTemplate(models.Model):
    """
    Template for recurring vehicle inspections.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="checklist_templates",
        verbose_name="Usuário",
    )
    name = models.CharField(max_length=100, verbose_name="Nome do Modelo")
    description = models.TextField(blank=True, verbose_name="Descrição")
    is_system = models.BooleanField(default=False, verbose_name="Modelo Padrão do Sistema")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Modelo de Checklist"
        verbose_name_plural = "Modelos de Checklist"
        ordering = ["-is_system", "name"]

    def __str__(self):
        return f"{self.name} (Sistema)" if self.is_system else self.name


class ChecklistTemplateItem(models.Model):
    """
    An item belonging to an inspection template.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Modelo",
    )
    category = models.CharField(max_length=50, default="Geral", verbose_name="Categoria")
    title = models.CharField(max_length=150, verbose_name="Item a Checar")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    is_required = models.BooleanField(default=True, verbose_name="Obrigatório")

    class Meta:
        verbose_name = "Item de Modelo de Checklist"
        verbose_name_plural = "Itens de Modelo de Checklist"
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.category}: {self.title}"


class ChecklistInspection(models.Model):
    """
    An actual inspection run for a vehicle.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="checklists",
        verbose_name="Veículo",
    )
    template = models.ForeignKey(
        ChecklistTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspections",
        verbose_name="Modelo Utilizado",
    )
    title = models.CharField(max_length=150, verbose_name="Título da Inspeção")
    odometer = models.PositiveIntegerField(null=True, blank=True, verbose_name="Odômetro (km)")
    checked_at = models.DateTimeField(default=timezone.now, verbose_name="Data/Hora da Inspeção")
    status = models.CharField(
        max_length=20,
        choices=InspectionStatus.choices,
        default=InspectionStatus.APPROVED,
        verbose_name="Status Geral",
    )
    notes = models.TextField(blank=True, verbose_name="Observações Gerais")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Inspeção / Checklist"
        verbose_name_plural = "Inspeções e Checklists"
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["vehicle", "checked_at"]),
            models.Index(fields=["vehicle", "status"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.vehicle.name} ({self.get_status_display()})"

    def evaluate_status(self):
        """Automatically compute overall inspection status based on item statuses."""
        item_statuses = set(self.items.values_list("status", flat=True))
        if not item_statuses:
            self.status = InspectionStatus.PENDING
            return

        if ItemStatus.PROBLEM in item_statuses:
            self.status = InspectionStatus.REJECTED
        elif ItemStatus.ATTENTION in item_statuses:
            self.status = InspectionStatus.WARNING
        else:
            self.status = InspectionStatus.APPROVED

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.odometer and self.vehicle_id:
            self.vehicle.update_odometer_cache(self.odometer)


class ChecklistInspectionItem(models.Model):
    """
    Individual item evaluated during an inspection.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection = models.ForeignKey(
        ChecklistInspection,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Inspeção",
    )
    category = models.CharField(max_length=50, default="Geral", verbose_name="Categoria")
    title = models.CharField(max_length=150, verbose_name="Item")
    status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.OK,
        verbose_name="Status",
    )
    notes = models.CharField(max_length=255, blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Item de Inspeção"
        verbose_name_plural = "Itens de Inspeção"
        ordering = ["category", "title"]

    def __str__(self):
        return f"{self.title}: {self.get_status_display()}"

