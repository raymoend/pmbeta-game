"""
Django management command to clean all player-created entities from the map
Usage: python manage.py cleanmap
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import *
from main.flag_models import *
from main.building_models import *


class Command(BaseCommand):
    help = 'Clean all player-created entities from the map (flags, NPCs, resources, buildings, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without interactive prompt',
        )
        parser.add_argument(
            '--keep-characters',
            action='store_true',
            help='Keep player characters, only delete map entities',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('🗺️  PMBeta Map Cleanup Tool')
        )
        self.stdout.write('This will remove ALL player-created entities from the map.')
        
        # Count entities before deletion
        counts = self.count_entities()
        
        if not counts['total']:
            self.stdout.write(
                self.style.SUCCESS('✅ Map is already clean! No entities to remove.')
            )
            return
        
        self.stdout.write('\n📊 Entities found on map:')
        for entity_type, count in counts.items():
            if entity_type != 'total' and count > 0:
                self.stdout.write(f'  • {entity_type}: {count}')
        
        self.stdout.write(f'\n🔥 Total entities to delete: {counts["total"]}')
        
        # Confirmation
        if not options['confirm']:
            confirm = input('\nAre you sure you want to delete ALL these entities? (yes/no): ')
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(self.style.ERROR('❌ Cleanup cancelled.'))
                return
        
        # Perform cleanup
        with transaction.atomic():
            deleted_counts = self.cleanup_entities(keep_characters=options['keep_characters'])
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Map cleanup completed!')
        )
        
        self.stdout.write('📋 Deleted entities:')
        for entity_type, count in deleted_counts.items():
            if count > 0:
                self.stdout.write(f'  • {entity_type}: {count}')
        
        self.stdout.write(
            self.style.SUCCESS('\n🗺️  Map is now clean and ready for fresh gameplay!')
        )

    def count_entities(self):
        """Count all player-created entities on the map"""
        counts = {}
        
        try:
            counts['Territory Flags'] = TerritoryFlag.objects.count()
        except:
            counts['Territory Flags'] = 0
            
        try:
            counts['NPCs'] = NPC.objects.count()
        except:
            counts['NPCs'] = 0
            
        try:
            counts['Resources'] = Resource.objects.count()
        except:
            counts['Resources'] = 0
            
        try:
            counts['Buildings'] = Building.objects.count()
        except:
            counts['Buildings'] = 0
            
        try:
            counts['Structures'] = Structure.objects.count()
        except:
            counts['Structures'] = 0
            
        try:
            counts['Combat Logs'] = CombatLog.objects.count()
        except:
            counts['Combat Logs'] = 0
            
        try:
            counts['Items'] = InventoryItem.objects.count()
        except:
            counts['Items'] = 0
            
        try:
            counts['Quests'] = Quest.objects.count()
        except:
            counts['Quests'] = 0
            
        try:
            counts['Player Characters'] = Character.objects.count()
        except:
            counts['Player Characters'] = 0
        
        counts['total'] = sum(count for count in counts.values())
        return counts

    def cleanup_entities(self, keep_characters=False):
        """Delete all player-created entities"""
        deleted_counts = {}
        
        # Territory Flags
        try:
            count = TerritoryFlag.objects.count()
            TerritoryFlag.objects.all().delete()
            deleted_counts['Territory Flags'] = count
            self.stdout.write(f'  🏴 Deleted {count} territory flags')
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not delete territory flags: {e}')
            deleted_counts['Territory Flags'] = 0
        
        # NPCs
        try:
            count = NPC.objects.count()
            NPC.objects.all().delete()
            deleted_counts['NPCs'] = count
            self.stdout.write(f'  👥 Deleted {count} NPCs')
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not delete NPCs: {e}')
            deleted_counts['NPCs'] = 0
        
        # Resources
        try:
            count = Resource.objects.count()
            Resource.objects.all().delete()
            deleted_counts['Resources'] = count
            self.stdout.write(f'  🌳 Deleted {count} resources')
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not delete resources: {e}')
            deleted_counts['Resources'] = 0
        
        # Buildings
        try:
            count = Building.objects.count()
            Building.objects.all().delete()
            deleted_counts['Buildings'] = count
            self.stdout.write(f'  🏠 Deleted {count} buildings')
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not delete buildings: {e}')
            deleted_counts['Buildings'] = 0
        
        # Structures
        try:
            count = Structure.objects.count()
            Structure.objects.all().delete()
            deleted_counts['Structures'] = count
            self.stdout.write(f'  🏛️ Deleted {count} structures')
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not delete structures: {e}')
            deleted_counts['Structures'] = 0
        
        # Combat Logs
        try:
            count = CombatLog.objects.count()
            CombatLog.objects.all().delete()
            deleted_counts['Combat Logs'] = count
            self.stdout.write(f'  ⚔️ Deleted {count} combat logs')
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not delete combat logs: {e}')
            deleted_counts['Combat Logs'] = 0
        
        # Inventory Items
        try:
            count = InventoryItem.objects.count()
            InventoryItem.objects.all().delete()
            deleted_counts['Inventory Items'] = count
            self.stdout.write(f'  🎒 Deleted {count} inventory items')
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not delete inventory items: {e}')
            deleted_counts['Inventory Items'] = 0
        
        # Quests
        try:
            count = Quest.objects.count()
            Quest.objects.all().delete()
            deleted_counts['Quests'] = count
            self.stdout.write(f'  📜 Deleted {count} quests')
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not delete quests: {e}')
            deleted_counts['Quests'] = 0
        
        # Player Characters (optional)
        if not keep_characters:
            try:
                count = Character.objects.count()
                Character.objects.all().delete()
                deleted_counts['Player Characters'] = count
                self.stdout.write(f'  👤 Deleted {count} player characters')
            except Exception as e:
                self.stdout.write(f'  ⚠️  Could not delete characters: {e}')
                deleted_counts['Player Characters'] = 0
        else:
            deleted_counts['Player Characters'] = 0
            self.stdout.write(f'  👤 Kept player characters (--keep-characters flag used)')
        
        return deleted_counts
