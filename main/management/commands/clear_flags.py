from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import TerritoryFlag, FlagLedger

class Command(BaseCommand):
    help = "Delete all territory flags and related ledgers. USE WITH CAUTION."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm deletion without interactive prompt",
        )

    def handle(self, *args, **options):
        confirm = options.get("yes")
        if not confirm:
            self.stdout.write(self.style.WARNING(
                "This will permanently delete ALL TerritoryFlag records and their ledgers."
            ))
            self.stdout.write(self.style.WARNING(
                "Re-run with --yes to proceed."
            ))
            return

        with transaction.atomic():
            ledgers_deleted, _ = FlagLedger.objects.all().delete()
            flags_deleted, _ = TerritoryFlag.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {flags_deleted} flags and {ledgers_deleted} ledger rows."
        ))

