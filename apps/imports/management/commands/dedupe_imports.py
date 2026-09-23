"""
Management command to remove duplicate Drivvo-imported records.

Re-importing the same Drivvo CSV used to create duplicate Refueling and Expense
rows (imports are now idempotent, but data imported before that fix can still
contain copies). This command groups records by their natural key
(vehicle + date + amounts, etc.), keeps the oldest copy, and deletes the rest.

Safe by default: run without arguments to preview what would be removed;
pass ``--apply`` to actually delete the duplicates.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.expenses.models import Expense
from apps.fuel.models import Refueling
from apps.vehicles.models import Vehicle

# Natural keys used to detect duplicated records.
REFUELING_KEY = ("occurred_at", "odometer", "liters", "total_amount")
EXPENSE_KEY = (
    "occurred_at",
    "amount",
    "category_id",
    "odometer",
    "vendor_name",
    "notes",
)


def _find_duplicates(queryset, key_fields):
    """Group records by ``key_fields``; return (kept, duplicates)."""
    keep = {}
    duplicates = []
    for obj in queryset.order_by("created_at", "id"):
        key = tuple(getattr(obj, field) for field in key_fields)
        if key in keep:
            duplicates.append(obj)
        else:
            keep[key] = obj
    return list(keep.values()), duplicates


class Command(BaseCommand):
    help = (
        "Remove duplicate Refueling/Expense rows created by repeated Drivvo "
        "imports (dry run by default; use --apply to delete)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            dest="apply",
            default=False,
            help="Actually delete the duplicates (default is a dry run).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        refuelings_removed = 0
        expenses_removed = 0
        affected_vehicles = set()

        for vehicle in Vehicle.objects.all().iterator():
            _, refueling_dups = _find_duplicates(
                Refueling.objects.filter(vehicle=vehicle), REFUELING_KEY
            )
            _, expense_dups = _find_duplicates(
                Expense.objects.filter(vehicle=vehicle).select_related("category"),
                EXPENSE_KEY,
            )

            for dup in refueling_dups:
                self.stdout.write(
                    f"  [abastecimento] {dup.occurred_at} | {dup.odometer} km | "
                    f"{dup.liters} L | R$ {dup.total_amount} (veículo: {vehicle.name})"
                )
            for dup in expense_dups:
                category_name = dup.category.name if dup.category else "Sem categoria"
                self.stdout.write(
                    f"  [despesa] {dup.occurred_at} | R$ {dup.amount} "
                    f"| {category_name} (veículo: {vehicle.name})"
                )

            refuelings_removed += len(refueling_dups)
            expenses_removed += len(expense_dups)
            if refueling_dups:
                affected_vehicles.add(vehicle.id)

            if apply_changes:
                with transaction.atomic():
                    Refueling.objects.filter(
                        pk__in=[dup.pk for dup in refueling_dups]
                    ).delete()
                    Expense.objects.filter(
                        pk__in=[dup.pk for dup in expense_dups]
                    ).delete()

        if apply_changes and affected_vehicles:
            # Recalculate consumption for vehicles whose refuelings changed so
            # dashboard/detail stats stay consistent.
            from apps.fuel.calculators import ConsumptionCalculator

            for vehicle in Vehicle.objects.filter(pk__in=affected_vehicles):
                ConsumptionCalculator.recalculate_vehicle_consumption(vehicle)

        if apply_changes:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Removidos {refuelings_removed} abastecimento(s) e "
                    f"{expenses_removed} despesa(s) duplicada(s)."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run: {refuelings_removed} abastecimento(s) e "
                    f"{expenses_removed} despesa(s) duplicada(s) encontrados. "
                    "Re-execute com --apply para remover."
                )
            )
