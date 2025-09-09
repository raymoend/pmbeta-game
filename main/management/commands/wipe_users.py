"""
Delete all non-superuser users (players). Optionally include superusers.
Usage:
  python manage.py wipe_users [--include-superusers]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


class Command(BaseCommand):
    help = "Delete all non-superuser users (players). Use --include-superusers to delete ALL users."

    def add_arguments(self, parser):
        parser.add_argument('--include-superusers', action='store_true', help='Also delete superuser accounts (DANGEROUS)')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        qs = User.objects.all()
        if not options.get('include_superusers'):
            qs = qs.filter(is_superuser=False)
        count = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted users: {count}{' (including superusers)' if options.get('include_superusers') else ''}"))

