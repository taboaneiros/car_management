"""
Services for processing offline synchronization payloads.
"""
from decimal import Decimal
import logging
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.vehicles.models import Vehicle
from apps.fuel.models import Refueling, FuelType
from apps.fuel.calculators import ConsumptionCalculator
from apps.expenses.models import Expense, ExpenseCategory
from apps.maintenance.models import Maintenance, ServiceType
from apps.reminders.models import Reminder, ReminderType, ReminderStatus
from apps.checklists.models import (
    ChecklistInspection,
    ChecklistInspectionItem,
    ChecklistTemplate,
    ItemStatus,
)
from apps.trips.models import Trip, TripPurpose

logger = logging.getLogger(__name__)


class SyncProcessingService:
    """
    Handles validating and persisting offline records submitted by the client PWA.
    """

    @classmethod
    def process_batch(cls, user, records):
        """
        Process a list of offline records for a given user.
        Each record has:
          {
            "id": client_uuid,
            "entity_type": "fuel" | "expense" | "maintenance" | "reminder" | "checklist" | "trip",
            "created_offline_at": iso_str,
            "payload": { ... }
          }
        Returns:
          {
            "total": int,
            "synced": int,
            "failed": int,
            "results": [
              {"id": client_uuid, "status": "synced"|"error", "server_id": str|None, "message": str}
            ]
          }
        """
        results = []
        synced_count = 0
        failed_count = 0

        for item in records:
            client_id = item.get("id")
            entity_type = item.get("entity_type")
            payload = item.get("payload", {})

            try:
                with transaction.atomic():
                    server_id = cls._process_single_record(user, entity_type, payload)
                    results.append({
                        "id": client_id,
                        "status": "synced",
                        "server_id": str(server_id),
                        "message": "Sincronizado com sucesso.",
                    })
                    synced_count += 1
            except Exception as exc:
                logger.warning(
                    "Erro ao sincronizar registro offline %s (%s): %s",
                    client_id, entity_type, exc
                )
                results.append({
                    "id": client_id,
                    "status": "error",
                    "server_id": None,
                    "message": str(exc),
                })
                failed_count += 1

        return {
            "total": len(records),
            "synced": synced_count,
            "failed": failed_count,
            "results": results,
        }

    @classmethod
    def _get_user_vehicle(cls, user, vehicle_id):
        """Retrieve vehicle ensuring it belongs to the user."""
        try:
            return Vehicle.objects.get(id=vehicle_id, owner_primary=user, is_active=True)
        except Vehicle.DoesNotExist:
            raise ValueError(f"Veículo com ID {vehicle_id} não encontrado ou inativo.")

    @classmethod
    def _process_single_record(cls, user, entity_type, payload):
        vehicle_id = payload.get("vehicle") or payload.get("vehicle_id")
        if not vehicle_id:
            raise ValueError("ID do veículo é obrigatório.")

        vehicle = cls._get_user_vehicle(user, vehicle_id)

        if entity_type == "fuel":
            return cls._sync_refueling(user, vehicle, payload)
        elif entity_type == "expense":
            return cls._sync_expense(user, vehicle, payload)
        elif entity_type == "maintenance":
            return cls._sync_maintenance(user, vehicle, payload)
        elif entity_type == "reminder":
            return cls._sync_reminder(user, vehicle, payload)
        elif entity_type == "checklist":
            return cls._sync_checklist(user, vehicle, payload)
        elif entity_type == "trip":
            return cls._sync_trip(user, vehicle, payload)
        else:
            raise ValueError(f"Tipo de entidade desconhecido: '{entity_type}'.")

    @classmethod
    def _sync_refueling(cls, user, vehicle, payload):
        occurred_at = parse_date(str(payload.get("occurred_at"))) or timezone.localdate()
        odometer = int(payload.get("odometer", 0))
        liters = Decimal(str(payload.get("liters", "0")).replace(",", "."))
        total_amount = Decimal(str(payload.get("total_amount", "0")).replace(",", "."))
        price_per_liter = None
        if payload.get("price_per_liter"):
            price_per_liter = Decimal(str(payload.get("price_per_liter")).replace(",", "."))
        elif liters > 0 and total_amount > 0:
            price_per_liter = (total_amount / liters).quantize(Decimal("0.001"))

        fuel_type = None
        fuel_type_id = payload.get("fuel_type") or payload.get("fuel_type_id")
        if fuel_type_id:
            fuel_type = FuelType.objects.filter(id=fuel_type_id, is_active=True).first()
        if not fuel_type:
            fuel_type = FuelType.objects.filter(is_active=True).first()

        refueling = Refueling.objects.create(
            vehicle=vehicle,
            occurred_at=occurred_at,
            station_name=payload.get("station_name", "Posto Não Informado"),
            odometer=odometer,
            liters=liters,
            total_amount=total_amount,
            price_per_liter=price_per_liter,
            fuel_type=fuel_type,
            is_full_tank=bool(payload.get("is_full_tank", True)),
            is_partial=bool(payload.get("is_partial", False)),
            missed_previous_fillup=bool(payload.get("missed_previous_fillup", False)),
            notes=payload.get("notes", ""),
        )

        vehicle.update_odometer_cache(odometer)
        ConsumptionCalculator.update_refueling_consumption(refueling)
        return refueling.id

    @classmethod
    def _sync_expense(cls, user, vehicle, payload):
        occurred_at = parse_date(str(payload.get("occurred_at"))) or timezone.localdate()
        amount = Decimal(str(payload.get("amount", "0")).replace(",", "."))
        category_id = payload.get("category") or payload.get("category_id")
        category = None
        if category_id:
            category = ExpenseCategory.objects.filter(id=category_id, is_active=True).first()
        if not category:
            category = ExpenseCategory.objects.filter(is_active=True).first()

        odometer = payload.get("odometer")
        if odometer:
            odometer = int(odometer)
            vehicle.update_odometer_cache(odometer)

        expense = Expense.objects.create(
            vehicle=vehicle,
            category=category,
            occurred_at=occurred_at,
            amount=amount,
            description=payload.get("description", "Despesa Offline"),
            odometer=odometer,
            vendor_name=payload.get("vendor_name", ""),
            is_recurring=bool(payload.get("is_recurring", False)),
            notes=payload.get("notes", ""),
        )
        return expense.id

    @classmethod
    def _sync_maintenance(cls, user, vehicle, payload):
        occurred_at = parse_date(str(payload.get("occurred_at"))) or timezone.localdate()
        odometer = int(payload.get("odometer", 0))
        total_amount = Decimal(str(payload.get("total_amount", "0")).replace(",", "."))
        service_type_id = payload.get("service_type") or payload.get("service_type_id")
        service_type = None
        if service_type_id:
            service_type = ServiceType.objects.filter(id=service_type_id, is_active=True).first()

        maintenance = Maintenance.objects.create(
            vehicle=vehicle,
            service_type=service_type,
            maintenance_type=payload.get("maintenance_type", "preventive"),
            occurred_at=occurred_at,
            odometer=odometer,
            total_amount=total_amount,
            workshop_name=payload.get("workshop_name", ""),
            description=payload.get("description", "Manutenção Offline"),
            notes=payload.get("notes", ""),
        )
        vehicle.update_odometer_cache(odometer)
        return maintenance.id

    @classmethod
    def _sync_reminder(cls, user, vehicle, payload):
        due_date = parse_date(str(payload.get("due_date", ""))) if payload.get("due_date") else None
        due_odometer = int(payload.get("due_odometer")) if payload.get("due_odometer") else None

        service_type_id = payload.get("service_type") or payload.get("service_type_id")
        service_type = None
        if service_type_id:
            service_type = ServiceType.objects.filter(id=service_type_id, is_active=True).first()

        reminder = Reminder(
            vehicle=vehicle,
            service_type=service_type,
            title=payload.get("title", "Lembrete"),
            reminder_type=payload.get("reminder_type", ReminderType.MAINTENANCE),
            due_date=due_date,
            due_odometer=due_odometer,
            alert_days_before=int(payload.get("alert_days_before", 7)),
            alert_odometer_before=int(payload.get("alert_odometer_before", 500)),
            is_recurring=bool(payload.get("is_recurring", False)),
            recurrence_interval_months=int(payload.get("recurrence_interval_months")) if payload.get("recurrence_interval_months") else None,
            recurrence_interval_km=int(payload.get("recurrence_interval_km")) if payload.get("recurrence_interval_km") else None,
            status=payload.get("status", ReminderStatus.PENDING),
            notes=payload.get("notes", ""),
        )
        reminder.save()
        return reminder.id

    @classmethod
    def _sync_checklist(cls, user, vehicle, payload):
        checked_at = parse_datetime(str(payload.get("checked_at", ""))) if payload.get("checked_at") else timezone.now()
        if not checked_at:
            checked_at = timezone.now()

        template_id = payload.get("template") or payload.get("template_id")
        template = None
        if template_id:
            template = ChecklistTemplate.objects.filter(id=template_id, is_active=True).first()
        if not template:
            template = ChecklistTemplate.objects.filter(is_active=True).first()

        odometer = payload.get("odometer")
        if odometer:
            odometer = int(odometer)
            vehicle.update_odometer_cache(odometer)

        inspection = ChecklistInspection.objects.create(
            vehicle=vehicle,
            template=template,
            title=payload.get("title") or (template.name if template else "Inspeção Offline"),
            odometer=odometer,
            checked_at=checked_at,
            notes=payload.get("notes", ""),
        )

        items_data = payload.get("items", [])
        if isinstance(items_data, list) and items_data:
            for it in items_data:
                ChecklistInspectionItem.objects.create(
                    inspection=inspection,
                    title=it.get("title", "Item de Inspeção"),
                    category=it.get("category", "Geral"),
                    status=it.get("status", ItemStatus.OK),
                    notes=it.get("notes", ""),
                )
        elif template:
            # If no individual item payload, seed from template items
            for tmpl_item in template.items.all():
                ChecklistInspectionItem.objects.create(
                    inspection=inspection,
                    title=tmpl_item.title,
                    category=tmpl_item.category,
                    status=ItemStatus.OK,
                    notes="",
                )

        inspection.evaluate_status()
        inspection.save()
        return inspection.id

    @classmethod
    def _sync_trip(cls, user, vehicle, payload):
        started_at = parse_datetime(str(payload.get("started_at", ""))) if payload.get("started_at") else timezone.now()
        ended_at = parse_datetime(str(payload.get("ended_at", ""))) if payload.get("ended_at") else None
        start_odometer = int(payload.get("start_odometer", vehicle.current_odometer_cache))
        end_odometer = int(payload.get("end_odometer")) if payload.get("end_odometer") else None

        rate_per_km = None
        if payload.get("rate_per_km"):
            rate_per_km = Decimal(str(payload.get("rate_per_km")).replace(",", "."))

        trip = Trip.objects.create(
            vehicle=vehicle,
            started_at=started_at,
            ended_at=ended_at,
            start_odometer=start_odometer,
            end_odometer=end_odometer,
            origin=payload.get("origin", "Origem Não Informada"),
            destination=payload.get("destination", "Destino Não Informado"),
            purpose=payload.get("purpose", TripPurpose.PERSONAL),
            rate_per_km=rate_per_km,
            driver_name=payload.get("driver_name", ""),
            notes=payload.get("notes", ""),
        )
        if end_odometer:
            vehicle.update_odometer_cache(end_odometer)
        return trip.id
