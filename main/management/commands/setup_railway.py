"""
Management command to setup Railway deployment
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from main.views_rpg import create_starter_items, create_monster_templates, create_basic_regions

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup Railway deployment with initial data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='Password for admin user (default: admin123)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Railway setup...'))
        
        # Create superuser
        admin_password = options['admin_password']
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@theshatteredrealm.com', admin_password)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Admin user created: admin/{admin_password}')
            )
        else:
            self.stdout.write(self.style.WARNING('→ Admin user already exists'))

        # Initialize game data
        try:
            self.stdout.write('Initializing starter items...')
            create_starter_items()
            self.stdout.write(self.style.SUCCESS('✓ Starter items created'))

            self.stdout.write('Initializing monster templates...')
            create_monster_templates()
            self.stdout.write(self.style.SUCCESS('✓ Monster templates created'))

            self.stdout.write('Initializing world regions...')
            create_basic_regions()
            self.stdout.write(self.style.SUCCESS('✓ World regions created'))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error initializing game data: {e}')
            )

        self.stdout.write(
            self.style.SUCCESS('🚀 Railway setup complete! The Shattered Realm is ready.')
        )
