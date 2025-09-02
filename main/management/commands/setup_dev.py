from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from main.models import Character
from main.views_rpg import create_starter_items, create_monster_templates
from django.conf import settings

class Command(BaseCommand):
    help = "Set up development data: admin user, character, starter items, monster templates."

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='Admin username to create if missing')
        parser.add_argument('--password', default=None, help='Admin password (defaults to DEV_ADMIN_PASSWORD env or admin123)')
        parser.add_argument('--email', default='admin@example.com')
        parser.add_argument('--lat', type=float, default=None, help='Initial character latitude')
        parser.add_argument('--lon', type=float, default=None, help='Initial character longitude')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password'] or (settings.__dict__.get('DEV_ADMIN_PASSWORD') if hasattr(settings, 'DEV_ADMIN_PASSWORD') else None)
        if not password:
            import os
            password = os.environ.get('DEV_ADMIN_PASSWORD', 'admin123')
        email = options['email']

        # Create admin user if missing
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin user '{username}'"))
        else:
            self.stdout.write(self.style.WARNING(f"Admin user '{username}' already exists"))

        # Create character if missing
        ch = getattr(user, 'character', None)
        if ch is None:
            lat = options['lat'] if options['lat'] is not None else float(getattr(settings, 'GAME_SETTINGS', {}).get('DEFAULT_START_LAT', 41.0646633))
            lon = options['lon'] if options['lon'] is not None else float(getattr(settings, 'GAME_SETTINGS', {}).get('DEFAULT_START_LON', -80.6391736))
            ch = Character.objects.create(
                user=user,
                name=username.capitalize(),
                lat=lat,
                lon=lon,
            )
            # Apply class base stats and save
            ch.apply_class_base_stats()
            ch.save()
            self.stdout.write(self.style.SUCCESS(f"Created character '{ch.name}' at {lat},{lon}"))
        else:
            self.stdout.write(self.style.WARNING(f"Character '{ch.name}' already exists"))

        # Seed starter items and monster templates
        try:
            create_starter_items()
            self.stdout.write(self.style.SUCCESS("Seeded starter item templates"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Starter items seeding skipped: {e}"))
        try:
            create_monster_templates()
            self.stdout.write(self.style.SUCCESS("Seeded monster templates"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Monster templates seeding skipped: {e}"))

        self.stdout.write(self.style.SUCCESS("Development setup complete."))

