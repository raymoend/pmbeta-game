"""
Management command to handle NPC respawning
Should be run periodically (every minute) via cron or task scheduler
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Flag, NPC


class Command(BaseCommand):
    help = 'Respawn dead NPCs that are ready to respawn'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print detailed output about respawn actions'
        )
    
    def handle(self, *args, **options):
        verbose = options['verbose']
        
        # Get all active flags
        active_flags = Flag.objects.filter(status='active')
        
        total_respawned = 0
        
        for flag in active_flags:
            # Try to respawn dead NPCs for this flag
            respawned_npcs = flag.respawn_dead_npcs()
            total_respawned += len(respawned_npcs)
            
            if verbose and respawned_npcs:
                self.stdout.write(
                    f"Flag '{flag.name}': Respawned {len(respawned_npcs)} NPCs"
                )
                for npc in respawned_npcs:
                    self.stdout.write(f"  - {npc.name} (Level {npc.level})")
        
        if verbose:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully respawned {total_respawned} NPCs across {active_flags.count()} flags'
                )
            )
        elif total_respawned > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Respawned {total_respawned} NPCs'
                )
            )
