import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.vehicles.models import Vehicle


class TripPurpose(models.TextChoices):
    """Purpose/category of a trip."""
    PERSONAL = "personal", "Pessoal"
    BUSINESS = "business", "Trabalho / Negócios"
    COMMUTE = "commute", "Deslocamento diário"
    FREIGHT = "freight", "Frete / Carga"
    OTHER = "other", "Outro"


class Trip(models.Model):
    """
    Represents a trip or route driven by a vehicle.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="trips",
        verbose_name="Veículo",
    )
    started_at = models.DateTimeField(
        verbose_name="Data e Hora Inicial",
        default=timezone.now,
    )
    ended_at = models.DateTimeField(
        verbose_name="Data e Hora Final",
        null=True,
        blank=True,
    )
    start_odometer = models.PositiveIntegerField(
        verbose_name="Odômetro Inicial (km)",
    )
    end_odometer = models.PositiveIntegerField(
        verbose_name="Odômetro Final (km)",
        null=True,
        blank=True,
    )
    distance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Distância (km)",
        help_text="Calculada automaticamente ou informada manualmente.",
    )
    origin = models.CharField(
        max_length=150,
        verbose_name="Origem",
    )
    destination = models.CharField(
        max_length=150,
        verbose_name="Destino",
    )
    purpose = models.CharField(
        max_length=20,
        choices=TripPurpose.choices,
        default=TripPurpose.PERSONAL,
        verbose_name="Finalidade",
    )
    rate_per_km = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Valor por km (R$/km)",
        help_text="Taxa para reembolso ou custo unitário.",
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valor Total (R$)",
        help_text="Custo total ou valor reembolsado.",
    )
    driver_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Motorista",
    )
    freight_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valor do Frete (R$)",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observações",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Viagem / Percurso"
        verbose_name_plural = "Viagens e Percursos"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["vehicle", "started_at"]),
            models.Index(fields=["vehicle", "purpose"]),
        ]

    def __str__(self):
        dist_str = f"{self.distance:.1f} km" if self.distance else "em andamento"
        return f"{self.origin} → {self.destination} ({dist_str})"

    def clean(self):
        super().clean()
        if self.end_odometer is not None and self.start_odometer is not None:
            if self.end_odometer < self.start_odometer:
                raise ValidationError({
                    "end_odometer": "O odômetro final não pode ser menor que o odômetro inicial."
                })
        if self.ended_at is not None and self.started_at is not None:
            if self.ended_at < self.started_at:
                raise ValidationError({
                    "ended_at": "A data/hora final não pode ser anterior à data/hora inicial."
                })

    def save(self, *args, **kwargs):
        # Auto-compute distance from odometers if available
        if self.end_odometer is not None and self.start_odometer is not None:
            self.distance = Decimal(str(self.end_odometer - self.start_odometer))

        # Auto-compute total_cost from distance and rate_per_km if not set
        if self.total_cost is None and self.distance and self.rate_per_km:
            self.total_cost = (Decimal(str(self.distance)) * Decimal(str(self.rate_per_km))).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)

        # Update vehicle odometer cache if end_odometer is provided
        if self.end_odometer and self.vehicle_id:
            self.vehicle.update_odometer_cache(self.end_odometer)

