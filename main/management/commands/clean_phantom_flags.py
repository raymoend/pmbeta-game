"""
Management command to clean phantom flags and reset territory system
"""
from django.core.management.base import BaseCommand
from main.flag_models import TerritoryFlag, TerritoryZone
from main.models import Character
from django.db import transaction
from django.core.cache import cache
import math


class Command(BaseCommand):
    help = 'Clean phantom flags and reset territory system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation',
        )
        parser.add_argument(
            '--reset-all',
            action='store_true',
            help='Reset entire territory system',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('🧹 Starting phantom flag cleanup...')
        )
        
        # Show current state
        self.show_current_state()
        
        if not options['force']:
            confirm = input('\nProceed with cleanup? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('Cleanup cancelled.')
                return
        
        # Perform cleanup
        with transaction.atomic():
            if options['reset_all']:
                self.reset_all_territories()
            else:
                self.clean_phantom_flags()
        
        # Clear any caches
        self.clear_caches()
        
        # Show final state
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('🎉 Cleanup complete!'))
        self.show_current_state()
        
        self.stdout.write('\n' + self.style.SUCCESS(
            '✅ Territory system reset. Please refresh your browser to see changes.'
        ))

    def show_current_state(self):
        """Show current territory state"""
        territories = TerritoryFlag.objects.all()
        zones = TerritoryZone.objects.all()
        
        self.stdout.write(f'\n📊 Current State:')
        self.stdout.write(f'  Territory Flags: {territories.count()}')
        self.stdout.write(f'  Territory Zones: {zones.count()}')
        
        if territories.exists():
            self.stdout.write('\n🏴 Existing Territories:')
            for flag in territories:
                self.stdout.write(
                    f'  • {flag.custom_name or "Unnamed"} '
                    f'({flag.owner.name}) at ({flag.lat:.6f}, {flag.lon:.6f}) '
                    f'- Level {flag.level} - {flag.status}'
                )

    def clean_phantom_flags(self):
        """Clean phantom flags while preserving legitimate ones"""
        self.stdout.write('\n🔍 Analyzing territories for phantoms...')
        
        # Get all territories
        territories = list(TerritoryFlag.objects.all())
        cleaned_count = 0
        
        # Group by location to find duplicates
        location_groups = {}
        for territory in territories:
            # Round to 6 decimal places for grouping
            key = (round(territory.lat, 6), round(territory.lon, 6))
            if key not in location_groups:
                location_groups[key] = []
            location_groups[key].append(territory)
        
        # Find and remove duplicates
        for location, group in location_groups.items():
            if len(group) > 1:
                # Keep the most recent one, remove others
                group.sort(key=lambda x: x.created_at, reverse=True)
                keeper = group[0]
                duplicates = group[1:]
                
                self.stdout.write(
                    f'  🚫 Found {len(duplicates)} duplicates at {location}, '
                    f'keeping {keeper.custom_name or "Unnamed"} (ID: {keeper.id})'
                )
                
                for duplicate in duplicates:
                    self.stdout.write(f'    ❌ Removing {duplicate.custom_name or "Unnamed"} (ID: {duplicate.id})')
                    duplicate.delete()
                    cleaned_count += 1
        
        # Check for territories with invalid states
        invalid_territories = TerritoryFlag.objects.filter(
            current_hp__lt=0
        )
        
        for territory in invalid_territories:
            self.stdout.write(f'  🔧 Fixing invalid HP for {territory.custom_name}: {territory.current_hp} -> {territory.max_hp}')
            territory.current_hp = territory.max_hp
            territory.save()
        
        # Regenerate all zones
        self.regenerate_zones()
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Cleaned {cleaned_count} phantom flags')
        )

    def reset_all_territories(self):
        """Complete reset of territory system"""
        self.stdout.write('\n🔥 FULL RESET: Removing ALL territories...')
        
        # Count before deletion
        flag_count = TerritoryFlag.objects.count()
        zone_count = TerritoryZone.objects.count()
        
        # Delete all territory zones first
        TerritoryZone.objects.all().delete()
        self.stdout.write(f'  ❌ Deleted {zone_count} territory zones')
        
        # Delete all territory flags
        TerritoryFlag.objects.all().delete()
        self.stdout.write(f'  ❌ Deleted {flag_count} territory flags')
        
        self.stdout.write(
            self.style.WARNING('⚠️ ALL TERRITORIES HAVE BEEN REMOVED!')
        )

    def regenerate_zones(self):
        """Regenerate all territory zones"""
        self.stdout.write('\n🔄 Regenerating territory zones...')
        
        # Delete all existing zones
        zone_count = TerritoryZone.objects.count()
        TerritoryZone.objects.all().delete()
        self.stdout.write(f'  🗑️ Deleted {zone_count} old zones')
        
        # Regenerate zones for all territories
        territories = TerritoryFlag.objects.all()
        regenerated = 0
        
        for territory in territories:
            try:
                territory.regenerate_territory_zone()
                regenerated += 1
                self.stdout.write(f'  ✅ Regenerated zone for {territory.custom_name or "Unnamed"}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Failed to regenerate zone for {territory.id}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Regenerated {regenerated} territory zones')
        )

    def clear_caches(self):
        """Clear all relevant caches"""
        self.stdout.write('\n🧹 Clearing caches...')
        
        try:
            # Clear Django cache
            cache.clear()
            self.stdout.write('  ✅ Django cache cleared')
        except Exception as e:
            self.stdout.write(f'  ⚠️ Cache clear warning: {e}')
        
        # Clear any session-based caches if they exist
        try:
            from django.contrib.sessions.models import Session
            # Don't delete all sessions, just note
            session_count = Session.objects.count()
            self.stdout.write(f'  ℹ️ {session_count} active sessions (not cleared)')
        except Exception:
            pass

    def validate_territories(self):
        """Validate territory integrity"""
        self.stdout.write('\n🔍 Validating territories...')
        
        issues = []
        territories = TerritoryFlag.objects.all()
        
        for territory in territories:
            # Check HP
            if territory.current_hp < 0:
                issues.append(f'Territory {territory.id} has negative HP: {territory.current_hp}')
            
            if territory.current_hp > territory.max_hp:
                issues.append(f'Territory {territory.id} has HP over max: {territory.current_hp}/{territory.max_hp}')
            
            # Check coordinates
            if not (-90 <= territory.lat <= 90):
                issues.append(f'Territory {territory.id} has invalid latitude: {territory.lat}')
            
            if not (-180 <= territory.lon <= 180):
                issues.append(f'Territory {territory.id} has invalid longitude: {territory.lon}')
            
            # Check if zone exists
            if not hasattr(territory, 'zone') or not territory.zone:
                issues.append(f'Territory {territory.id} missing zone')
        
        if issues:
            self.stdout.write(self.style.WARNING('⚠️ Issues found:'))
            for issue in issues:
                self.stdout.write(f'  • {issue}')
        else:
            self.stdout.write(self.style.SUCCESS('✅ All territories validated successfully'))
        
        return len(issues) == 0
