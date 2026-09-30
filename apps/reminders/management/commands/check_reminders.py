"""
Management command to check pending reminders and dispatch email notifications.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.reminders.services import ReminderService

User = get_user_model()


class Command(BaseCommand):
    help = "Check pending reminders and send email alerts when due or overdue."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Simulate check without sending actual emails or updating timestamps.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default=False,
            help="Bypass the 24-hour notification throttling window.",
        )
        parser.add_argument(
            "--user",
            type=str,
            dest="user_email",
            default=None,
            help="Filter check to a specific user email.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]
        user_email = options["user_email"]

        target_user = None
        if user_email:
            try:
                target_user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User with email '{user_email}' not found."))
                return

        mode_str = " (DRY RUN)" if dry_run else ""
        self.stdout.write(f"Checking pending reminders{mode_str}...")

        result = ReminderService.check_and_send_notifications(
            user=target_user,
            force=force,
            dry_run=dry_run,
        )

        sent = result["sent_count"]
        skipped = result["skipped_count"]

        msg = f"Check complete. {sent} reminder email(s) processed/sent, {skipped} skipped (throttled)."
        self.stdout.write(self.style.SUCCESS(msg))

