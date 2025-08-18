"""
Management command to debug and fix territory flag issues
"""
from django.core.management.base import BaseCommand
from main.flag_models import TerritoryFlag, TerritoryZone
from main.models import Character
import math


class Command(BaseCommand):
    help = 'Debug and fix territory flag issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all territories',
        )
        parser.add_argument(
            '--cleanup-duplicates',
            action='store_true',
            help='Remove duplicate flags at same location',
        )
        parser.add_argument(
            '--fix-zones',
            action='store_true',
            help='Regenerate all territory zones',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by username',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_territories(options.get('user'))
        
        if options['cleanup_duplicates']:
            self.cleanup_duplicates()
        
        if options['fix_zones']:
            self.fix_territory_zones()

    def list_territories(self, username_filter=None):
        """List all territories with details"""
        territories = TerritoryFlag.objects.select_related('owner')
        
        if username_filter:
            territories = territories.filter(owner__user__username=username_filter)
        
        self.stdout.write(
            self.style.SUCCESS(f"Found {territories.count()} territories:")
        )
        
        for flag in territories:
            self.stdout.write(
                f"ID: {flag.id} | Owner: {flag.owner.name} | "
                f"Name: {flag.custom_name or 'Unnamed'} | "
                f"Level: {flag.level} | Status: {flag.status} | "
                f"Location: ({flag.lat:.6f}, {flag.lon:.6f}) | "
                f"Radius: {flag.radius_meters}m"
            )

    def cleanup_duplicates(self):
        """Remove duplicate flags at the same location"""
        self.stdout.write("Checking for duplicate territories...")
        
        # Find duplicates by checking lat/lon proximity
        territories = list(TerritoryFlag.objects.all())
        duplicates_found = 0
        removed_count = 0
        
        for i, flag1 in enumerate(territories):
            if not TerritoryFlag.objects.filter(id=flag1.id).exists():
                continue  # Already deleted
                
            for j, flag2 in enumerate(territories[i+1:], i+1):
                if not TerritoryFlag.objects.filter(id=flag2.id).exists():
                    continue  # Already deleted
                
                # Calculate distance between flags
                distance = self.calculate_distance(
                    flag1.lat, flag1.lon,
                    flag2.lat, flag2.lon
                )
                
                # If flags are within 10 meters, consider them duplicates
                if distance < 10:
                    duplicates_found += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Found duplicate: {flag1.custom_name or 'Unnamed'} "
                            f"and {flag2.custom_name or 'Unnamed'} "
                            f"({distance:.1f}m apart)"
                        )
                    )
                    
                    # Keep the newer one (higher ID), delete the older
                    if flag1.created_at < flag2.created_at:
                        self.stdout.write(f"Removing older flag: {flag1.id}")
                        flag1.delete()
                        removed_count += 1
                        break  # Break inner loop since flag1 is deleted
                    else:
                        self.stdout.write(f"Removing older flag: {flag2.id}")
                        flag2.delete()
                        removed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup complete. Found {duplicates_found} duplicate groups, "
                f"removed {removed_count} flags."
            )
        )

    def fix_territory_zones(self):
        """Regenerate all territory zones"""
        self.stdout.write("Regenerating territory zones...")
        
        territories = TerritoryFlag.objects.all()
        fixed_count = 0
        
        for flag in territories:
            try:
                # Delete existing zone
                TerritoryZone.objects.filter(flag=flag).delete()
                
                # Regenerate zone
                flag.regenerate_territory_zone()
                fixed_count += 1
                
                self.stdout.write(f"Fixed zone for: {flag.custom_name or flag.id}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to fix zone for {flag.id}: {e}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Fixed {fixed_count} territory zones.")
        )

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in meters"""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
