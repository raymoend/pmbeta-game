"""
Management command for automated game maintenance tasks
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from main.models import Monster, Character, PvECombat, PvPCombat, Trade
from datetime import timedelta


class Command(BaseCommand):
    help = 'Perform automated game maintenance tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--respawn-monsters',
            action='store_true',
            help='Respawn dead monsters that are ready'
        )
        parser.add_argument(
            '--cleanup-old-combats',
            action='store_true',
            help='Clean up old completed combat sessions'
        )
        parser.add_argument(
            '--expire-trades',
            action='store_true',
            help='Expire old trade offers'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all maintenance tasks'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        """Execute maintenance tasks"""
        
        if options['all']:
            options['respawn_monsters'] = True
            options['cleanup_old_combats'] = True
            options['expire_trades'] = True
        
        if not any([options['respawn_monsters'], options['cleanup_old_combats'], options['expire_trades']]):
            self.stdout.write(
                self.style.WARNING('No maintenance tasks specified. Use --help for options.')
            )
            return
        
        self.stdout.write("Starting game maintenance...")
        
        if options['respawn_monsters']:
            self.respawn_monsters(options['dry_run'])
        
        if options['cleanup_old_combats']:
            self.cleanup_old_combats(options['dry_run'])
        
        if options['expire_trades']:
            self.expire_old_trades(options['dry_run'])
        
        self.stdout.write(
            self.style.SUCCESS('Game maintenance completed successfully!')
        )
    
    def respawn_monsters(self, dry_run=False):
        """Respawn monsters that are ready to respawn"""
        current_time = timezone.now()
        
        # Find monsters ready to respawn
        dead_monsters = Monster.objects.filter(
            is_alive=False,
            respawn_at__lte=current_time
        )
        
        count = dead_monsters.count()
        
        if dry_run:
            self.stdout.write(f"Would respawn {count} monsters")
            return
        
        if count == 0:
            self.stdout.write("No monsters ready to respawn")
            return
        
        respawned = 0
        for monster in dead_monsters:
            try:
                with transaction.atomic():
                    monster.respawn()
                    respawned += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to respawn monster {monster.id}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Respawned {respawned} monsters")
        )
    
    def cleanup_old_combats(self, dry_run=False):
        """Clean up old completed combat sessions"""
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # Clean up old PvE combats
        old_pve_combats = PvECombat.objects.filter(
            ended_at__lt=cutoff_time,
            status__in=['victory', 'defeat', 'fled']
        )
        
        pve_count = old_pve_combats.count()
        
        # Clean up old PvP combats
        old_pvp_combats = PvPCombat.objects.filter(
            ended_at__lt=cutoff_time,
            status__in=['victory', 'declined', 'expired']
        )
        
        pvp_count = old_pvp_combats.count()
        
        if dry_run:
            self.stdout.write(f"Would delete {pve_count} old PvE combats")
            self.stdout.write(f"Would delete {pvp_count} old PvP combats")
            return
        
        if pve_count == 0 and pvp_count == 0:
            self.stdout.write("No old combat sessions to clean up")
            return
        
        # Delete old combats
        deleted_pve = old_pve_combats.delete()[0]
        deleted_pvp = old_pvp_combats.delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(f"Cleaned up {deleted_pve} PvE and {deleted_pvp} PvP combat sessions")
        )
    
    def expire_old_trades(self, dry_run=False):
        """Expire old trade offers"""
        current_time = timezone.now()
        
        expired_trades = Trade.objects.filter(
            expires_at__lt=current_time,
            status='pending'
        )
        
        count = expired_trades.count()
        
        if dry_run:
            self.stdout.write(f"Would expire {count} old trade offers")
            return
        
        if count == 0:
            self.stdout.write("No trade offers to expire")
            return
        
        # Update status to expired
        updated = expired_trades.update(status='expired')
        
        self.stdout.write(
            self.style.SUCCESS(f"Expired {updated} old trade offers")
        )
