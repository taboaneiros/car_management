"""
Import services for the imports app.

Contains the Drivvo import pipeline that persists parsed data into the
application models inside a single atomic transaction.
"""
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Set

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.expenses.models import Expense, ExpenseCategory
from apps.fuel.models import FuelType, Refueling
from apps.vehicles.models import Vehicle

from .drivvo_parser import map_expense_category, map_fuel_type


def _quantize_decimal(value: Any, places: int) -> Optional[Decimal]:
    """Quantize a Decimal to ``places`` decimal places or return None."""
    if value is None:
        return None
    try:
        decimal_value = Decimal(str(value))
        quantum = Decimal("1").scaleb(-places)
        return decimal_value.quantize(quantum)
    except (InvalidOperation, ValueError):
        return None


def _to_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to a non-negative int."""
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _default_vehicle_name(user) -> str:
    """Generate a fallback name for vehicles without a name in the CSV."""
    return f"Veículo {Vehicle.objects.filter(owner_primary=user).count() + 1}"


def _resolve_fuel_type(user, fuel_type_name: str) -> Optional[FuelType]:
    """
    Resolve (or create) a FuelType for the given canonical name.

    System fuel types (``user=None``) are shared by all users.
    """
    if not fuel_type_name:
        return None
    fuel_type = FuelType.objects.filter(
        Q(user=user) | Q(user=None),
        name__iexact=fuel_type_name,
        is_active=True,
    ).first()
    if fuel_type is None:
        fuel_type = FuelType.objects.create(
            user=user,
            name=fuel_type_name,
            is_active=True,
        )
    return fuel_type


def _resolve_expense_category(user, category_name: str) -> Optional[ExpenseCategory]:
    """
    Resolve (or create) an ExpenseCategory for the given name.

    System categories (``user=None``) are shared by all users.
    """
    if not category_name:
        category_name = "Outros"
    category = ExpenseCategory.objects.filter(
        Q(user=user) | Q(user=None),
        name__iexact=category_name,
        is_active=True,
    ).first()
    if category is None:
        category, _ = ExpenseCategory.objects.get_or_create(
            user=user,
            slug=slugify(category_name) or "outros",
            defaults={"name": category_name, "is_active": True},
        )
    return category


@transaction.atomic
def import_drivvo_data(user, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Import Drivvo data for the current user.

    Args:
        user: The authenticated user importing the data.
        parsed_data: Dict produced by the Drivvo parser with keys
            ``vehicles``, ``refuelings``, ``expenses`` and
            ``unsupported_sections``.

    Returns:
        A summary dict with the following keys:
        ``vehicles_created``, ``vehicles_updated``, ``refuelings_created``,
        ``refuelings_skipped``, ``expenses_created``, ``expenses_skipped``,
        ``warnings`` and ``errors``.
    """
    result = {
        "vehicles_created": 0,
        "vehicles_updated": 0,
        "refuelings_created": 0,
        "refuelings_skipped": 0,
        "expenses_created": 0,
        "expenses_skipped": 0,
        "warnings": [],
        "errors": [],
    }

    vehicle_map: Dict[str, Vehicle] = {}
    vehicles_to_recalculate: Set[Vehicle] = set()

    # ------------------------------------------------------------------
    # 1. Vehicles (create or update by plate / name + year)
    # ------------------------------------------------------------------
    for vehicle_data in parsed_data.get("vehicles", []):
        plate = (vehicle_data.get("plate") or "").strip().upper()
        name = (vehicle_data.get("name") or "").strip()
        year = vehicle_data.get("year")
        odometer = _to_int(vehicle_data.get("odometer") or 0)
        brand = (vehicle_data.get("brand") or "").strip()
        model = (vehicle_data.get("model") or "").strip()
        vehicle_type = vehicle_data.get("vehicle_type") or "car"
        is_active = vehicle_data.get("is_active", True)

        vehicle = None
        if plate:
            vehicle = Vehicle.objects.filter(
                owner_primary=user, plate__iexact=plate
            ).first()
        if vehicle is None and name and year:
            vehicle = Vehicle.objects.filter(
                owner_primary=user, name__iexact=name, year=year
            ).first()

        if vehicle is not None:
            vehicle.brand = brand or vehicle.brand
            vehicle.model = model or vehicle.model
            vehicle.vehicle_type = vehicle_type or vehicle.vehicle_type
            vehicle.is_active = is_active
            if year:
                vehicle.year = year
            if odometer:
                vehicle.current_odometer_cache = max(
                    vehicle.current_odometer_cache or 0, odometer
                )
                if not vehicle.initial_odometer:
                    vehicle.initial_odometer = odometer
            vehicle.save()
            result["vehicles_updated"] += 1
        else:
            vehicle = Vehicle.objects.create(
                owner_primary=user,
                name=name or _default_vehicle_name(user),
                brand=brand,
                model=model,
                year=year or timezone.now().year,
                vehicle_type=vehicle_type,
                plate=plate,
                initial_odometer=odometer,
                current_odometer_cache=odometer,
                is_active=is_active,
            )
            result["vehicles_created"] += 1

        if name:
            vehicle_map[name] = vehicle

    # ------------------------------------------------------------------
    # 2. Refuelings
    # ------------------------------------------------------------------
    for refueling_data in parsed_data.get("refuelings", []):
        vehicle_name = (refueling_data.get("vehicle_name") or "").strip()
        vehicle = vehicle_map.get(vehicle_name)
        if vehicle is None:
            result["warnings"].append(
                f"Abastecimento ignorado: veículo '{vehicle_name}' "
                "não encontrado no arquivo."
            )
            result["refuelings_skipped"] += 1
            continue

        occurred_at = refueling_data.get("occurred_at")
        if occurred_at is None:
            result["errors"].append(
                "Abastecimento ignorado: data inválida ou ausente."
            )
            result["refuelings_skipped"] += 1
            continue

        liters = refueling_data.get("liters")
        total_amount = refueling_data.get("total_amount")
        price_per_liter = refueling_data.get("price_per_liter")

        # Derive liters from total / price when the CSV does not provide it.
        if liters is None and total_amount is not None and price_per_liter:
            try:
                liters = Decimal(total_amount) / Decimal(price_per_liter)
            except (InvalidOperation, ZeroDivisionError):
                liters = None

        liters = _quantize_decimal(liters, 3)
        total_amount = _quantize_decimal(total_amount, 2)
        price_per_liter = _quantize_decimal(price_per_liter, 4)

        # The model requires liters > 0 and at least one of total/price so the
        # missing value can be derived in Refueling.save().
        if liters is None or liters <= 0 or (
            total_amount is None and price_per_liter is None
        ):
            result["errors"].append(
                f"Abastecimento de {occurred_at} ignorado: "
                "volume e valor/preço insuficientes."
            )
            result["refuelings_skipped"] += 1
            continue

        fuel_type = _resolve_fuel_type(
            user, map_fuel_type(refueling_data.get("fuel_type_name") or "")
        )

        odometer = _to_int(refueling_data.get("odometer") or 0)

        # Skip records that already exist so re-importing the same Drivvo file
        # does not duplicate data.
        already_exists = Refueling.objects.filter(
            vehicle=vehicle,
            occurred_at=occurred_at,
            odometer=odometer,
            liters=liters,
            total_amount=total_amount,
        ).exists()
        if already_exists:
            result["warnings"].append(
                f"Abastecimento de {occurred_at} ({liters} L) já existe; ignorado."
            )
            result["refuelings_skipped"] += 1
            continue

        Refueling.objects.create(
            vehicle=vehicle,
            occurred_at=occurred_at,
            odometer=odometer,
            liters=liters,
            total_amount=total_amount,
            price_per_liter=price_per_liter,
            fuel_type=fuel_type,
            is_full_tank=refueling_data.get("is_full_tank", False),
            station_name=(refueling_data.get("station_name") or "")[:100],
            notes=refueling_data.get("notes", ""),
        )
        vehicle.update_odometer_cache(odometer)
        vehicles_to_recalculate.add(vehicle)
        result["refuelings_created"] += 1

    # ------------------------------------------------------------------
    # 3. Expenses
    # ------------------------------------------------------------------
    for expense_data in parsed_data.get("expenses", []):
        vehicle_name = (expense_data.get("vehicle_name") or "").strip()
        vehicle = vehicle_map.get(vehicle_name)
        if vehicle is None:
            result["warnings"].append(
                f"Despesa ignorada: veículo '{vehicle_name}' "
                "não encontrado no arquivo."
            )
            result["expenses_skipped"] += 1
            continue

        occurred_at = expense_data.get("occurred_at")
        amount = _quantize_decimal(expense_data.get("amount"), 2)
        if occurred_at is None or amount is None:
            result["errors"].append(
                "Despesa ignorada: data ou valor inválido."
            )
            result["expenses_skipped"] += 1
            continue

        category = _resolve_expense_category(
            user, map_expense_category(expense_data.get("category_name") or "")
        )

        odometer = expense_data.get("odometer")
        odometer_value = _to_int(odometer) if odometer is not None else None
        vendor_name = (expense_data.get("vendor_name") or "")[:100]
        notes = expense_data.get("notes", "")

        # Skip records that already exist so re-importing the same Drivvo file
        # does not duplicate data.
        already_exists = Expense.objects.filter(
            vehicle=vehicle,
            occurred_at=occurred_at,
            amount=amount,
            category=category,
            odometer=odometer_value,
            vendor_name=vendor_name,
            notes=notes,
        ).exists()
        if already_exists:
            result["warnings"].append(
                f"Despesa de {occurred_at} (R$ {amount}) já existe; ignorada."
            )
            result["expenses_skipped"] += 1
            continue

        Expense.objects.create(
            vehicle=vehicle,
            occurred_at=occurred_at,
            amount=amount,
            category=category,
            odometer=odometer_value,
            vendor_name=vendor_name,
            notes=notes,
        )
        if odometer_value:
            vehicle.update_odometer_cache(odometer_value)
        result["expenses_created"] += 1

    # ------------------------------------------------------------------
    # 4. Recalculate consumption for the affected vehicles so the dashboard
    #    and detail pages stay consistent with the imported refuelings.
    # ------------------------------------------------------------------
    if vehicles_to_recalculate:
        from apps.fuel.calculators import ConsumptionCalculator

        for vehicle in vehicles_to_recalculate:
            ConsumptionCalculator.recalculate_vehicle_consumption(vehicle)

    # ------------------------------------------------------------------
    # 5. Report sections present in the file but not supported yet.
    # ------------------------------------------------------------------
    unsupported = parsed_data.get("unsupported_sections", [])
    if unsupported:
        result["warnings"].append(
            "Seções presentes no arquivo e não importadas: "
            f"{', '.join(unsupported)}."
        )

    return result
