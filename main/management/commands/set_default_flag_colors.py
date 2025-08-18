"""
Management command to set default flag colors for existing users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import Character
from main.building_models import FlagColor


class Command(BaseCommand):
    help = 'Set default red flag color for all existing users'

    def handle(self, *args, **options):
        # Get or create red flag color
        red_flag_color, created = FlagColor.objects.get_or_create(
            name='red',
            defaults={
                'hex_color': '#ff0000',
                'display_name': 'Red',
                'is_premium': False,
                'unlock_level': 1,
                'unlock_cost': 0,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created red flag color'))
        else:
            self.stdout.write(self.style.SUCCESS('Red flag color already exists'))
        
        # Update all characters without flag colors
        characters_updated = Character.objects.filter(flag_color__isnull=True).update(flag_color=red_flag_color)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {characters_updated} characters with red flag color')
        )
        
        # Create other basic flag colors if they don't exist
        basic_colors = [
            {'hex_color': '#ff8800', 'name': 'orange', 'display_name': 'Orange'},
            {'hex_color': '#ffff00', 'name': 'yellow', 'display_name': 'Yellow'},
            {'hex_color': '#00ff00', 'name': 'green', 'display_name': 'Green'},
            {'hex_color': '#0000ff', 'name': 'blue', 'display_name': 'Blue'},
            {'hex_color': '#ff00ff', 'name': 'purple', 'display_name': 'Purple'},
        ]
        
        colors_created = 0
        for color_data in basic_colors:
            color, created = FlagColor.objects.get_or_create(
                name=color_data['name'],
                defaults={
                    'hex_color': color_data['hex_color'],
                    'display_name': color_data['display_name'],
                    'is_premium': False,
                    'unlock_level': 1,
                    'unlock_cost': 0,
                    'is_active': True
                }
            )
            if created:
                colors_created += 1
        
        if colors_created > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {colors_created} additional flag colors')
            )
        
        self.stdout.write(self.style.SUCCESS('Flag color setup complete!'))
