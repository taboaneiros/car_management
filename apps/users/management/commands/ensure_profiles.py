"""
Management command to ensure all users have a profile.
Used for data sanitization of existing users without profiles.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import User, UserProfile


class Command(BaseCommand):
    help = "Create UserProfile for users that don't have one."

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
        
        # Find users without profiles
        users_without_profile = []
        for user in User.objects.all():
            if not hasattr(user, "profile"):
                try:
                    UserProfile.objects.get(user=user)
                except UserProfile.DoesNotExist:
                    users_without_profile.append(user)
        
        if not users_without_profile:
            self.stdout.write(
                self.style.SUCCESS("All users already have profiles. Nothing to do.")
            )
            return
        
        self.stdout.write(
            f"Found {len(users_without_profile)} user(s) without profile."
        )
        
        if dry_run:
            self.stdout.write("Dry run mode - would create profiles for:")
            for user in users_without_profile:
                self.stdout.write(f"  - {user.email}")
            return
        
        # Create profiles
        created_count = 0
        with transaction.atomic():
            for user in users_without_profile:
                UserProfile.objects.create(user=user)
                created_count += 1
                self.stdout.write(f"Created profile for: {user.email}")
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} profile(s).")
        )