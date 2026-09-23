"""
Management command to ensure all users have default fuel types and expense categories.
Used for data sanitization of existing users.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.users.models import User
from apps.fuel.models import FuelType
from apps.expenses.models import ExpenseCategory, CategoryKind


class Command(BaseCommand):
    help = "Create default fuel types and expense categories for users that don't have them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Show what would be done without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        
        default_fuel_types = [
            ("Gasolina Comum", "GAS"),
            ("Gasolina Aditivada", "GAS_ADT"),
            ("Etanol", "ET"),
            ("Diesel", "DI"),
            ("GNV", "GNV"),
        ]
        
        default_categories = [
            ("Estacionamento", CategoryKind.VARIABLE),
            ("Pedágio", CategoryKind.VARIABLE),
            ("Multa", CategoryKind.VARIABLE),
            ("Lavagem", CategoryKind.VARIABLE),
            ("Seguro", CategoryKind.FIXED),
            ("IPVA", CategoryKind.FIXED),
            ("Licenciamento", CategoryKind.FIXED),
            ("Manutenção", CategoryKind.VARIABLE),
            ("Revisão", CategoryKind.VARIABLE),
            ("Peças", CategoryKind.VARIABLE),
            ("Outros", CategoryKind.OTHER),
        ]
        
        users = User.objects.all()
        self.stdout.write(f"Processing {users.count()} user(s)...")
        
        if dry_run:
            self.stdout.write("Dry run mode - no changes will be made.")
        
        fuel_types_created = 0
        categories_created = 0
        
        with transaction.atomic():
            for user in users:
                # Create fuel types
                for name, code in default_fuel_types:
                    if dry_run:
                        exists = FuelType.objects.filter(user=user, code=code).exists()
                        if not exists:
                            fuel_types_created += 1
                            self.stdout.write(
                                f"  Would create fuel type '{name}' for {user.email}"
                            )
                    else:
                        _, created = FuelType.objects.get_or_create(
                            user=user,
                            code=code,
                            defaults={"name": name, "is_system": True}
                        )
                        if created:
                            fuel_types_created += 1
                            self.stdout.write(
                                f"  Created fuel type '{name}' for {user.email}"
                            )
                
                # Create expense categories
                for name, kind in default_categories:
                    if dry_run:
                        exists = ExpenseCategory.objects.filter(
                            user=user, slug=slugify(name)
                        ).exists()
                        if not exists:
                            categories_created += 1
                            self.stdout.write(
                                f"  Would create category '{name}' for {user.email}"
                            )
                    else:
                        _, created = ExpenseCategory.objects.get_or_create(
                            user=user,
                            slug=slugify(name),
                            defaults={"name": name, "kind": kind, "is_system": True}
                        )
                        if created:
                            categories_created += 1
                            self.stdout.write(
                                f"  Created category '{name}' for {user.email}"
                            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run complete. Would create {fuel_types_created} fuel type(s) "
                    f"and {categories_created} categor(y/ies)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {fuel_types_created} fuel type(s) "
                    f"and {categories_created} categor(y/ies)."
                )
            )