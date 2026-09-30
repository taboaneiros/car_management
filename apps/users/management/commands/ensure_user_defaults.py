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
        
        default_service_types = [
            ("Troca de Óleo e Filtro", 10000, 12),
            ("Filtro de Ar do Motor", 10000, 12),
            ("Filtro de Cabine (Ar Condicionado)", 10000, 12),
            ("Filtro de Combustível", 10000, 12),
            ("Pastilhas de Freio", 20000, 12),
            ("Fluido de Freio", 20000, 24),
            ("Correia Dentada", 50000, 48),
            ("Velas de Ignição", 20000, 24),
            ("Alinhamento e Balanceamento", 10000, 6),
            ("Bateria", None, 36),
            ("Revisão Preventiva Geral", 10000, 12),
        ]
        
        users = User.objects.all()
        self.stdout.write(f"Processing {users.count()} user(s)...")
        
        if dry_run:
            self.stdout.write("Dry run mode - no changes will be made.")
        
        fuel_types_created = 0
        categories_created = 0
        services_created = 0
        
        from apps.maintenance.models import ServiceType

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

                # Create default service types
                for name, km, months in default_service_types:
                    if dry_run:
                        exists = ServiceType.objects.filter(user=user, name=name).exists()
                        if not exists:
                            services_created += 1
                            self.stdout.write(
                                f"  Would create service type '{name}' for {user.email}"
                            )
                    else:
                        _, created = ServiceType.objects.get_or_create(
                            user=user,
                            name=name,
                            defaults={
                                "default_interval_km": km,
                                "default_interval_months": months,
                                "is_system": True,
                            }
                        )
                        if created:
                            services_created += 1
                            self.stdout.write(
                                f"  Created service type '{name}' for {user.email}"
                            )

            # Create system checklist templates if not present
            from apps.checklists.models import ChecklistTemplate, ChecklistTemplateItem

            default_templates = [
                (
                    "Inspeção Pré-Viagem",
                    "Checklist completo para viagens longas e trajetos rodoviários.",
                    [
                        ("Fluidos", "Nível do óleo do motor", 1),
                        ("Fluidos", "Líquido de arrefecimento (radiador)", 2),
                        ("Fluidos", "Fluido de freio", 3),
                        ("Fluidos", "Água do limpador de para-brisa", 4),
                        ("Pneus e Rodas", "Calibragem e desgaste dos 4 pneus", 5),
                        ("Pneus e Rodas", "Calibragem e estado do estepe", 6),
                        ("Iluminação", "Faróis dianteiros (baixo e alto)", 7),
                        ("Iluminação", "Lanternas, luzes de freio e ré", 8),
                        ("Iluminação", "Luzes de seta / pisca-alerta", 9),
                        ("Segurança", "Palhetas do limpador de para-brisa", 10),
                        ("Segurança", "Cintos de segurança de todos os ocupantes", 11),
                        ("Segurança", "Triângulo, macaco e chave de roda", 12),
                        ("Segurança", "Documentação do veículo e CNH", 13),
                    ],
                ),
                (
                    "Checagem Semanal Básica",
                    "Inspeção preventiva rápida para uso urbano no dia a dia.",
                    [
                        ("Fluidos", "Nível de óleo do motor", 1),
                        ("Fluidos", "Nível de água do radiador", 2),
                        ("Pneus", "Calibragem dos pneus", 3),
                        ("Iluminação", "Faróis e luzes de freio", 4),
                        ("Geral", "Verificação visual de vazamentos sob o veículo", 5),
                    ],
                ),
            ]

            templates_created = 0
            for tmpl_name, tmpl_desc, items in default_templates:
                if dry_run:
                    if not ChecklistTemplate.objects.filter(is_system=True, name=tmpl_name).exists():
                        templates_created += 1
                else:
                    tmpl, created = ChecklistTemplate.objects.get_or_create(
                        is_system=True,
                        name=tmpl_name,
                        defaults={"description": tmpl_desc, "is_active": True},
                    )
                    if created:
                        templates_created += 1
                        for cat, title, order in items:
                            ChecklistTemplateItem.objects.create(
                                template=tmpl,
                                category=cat,
                                title=title,
                                order=order,
                            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run complete. Would create {fuel_types_created} fuel type(s), "
                    f"{categories_created} categor(y/ies), {services_created} service type(s), "
                    f"and {templates_created} checklist template(s)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {fuel_types_created} fuel type(s), "
                    f"{categories_created} categor(y/ies), {services_created} service type(s), "
                    f"and {templates_created} checklist template(s)."
                )
            )