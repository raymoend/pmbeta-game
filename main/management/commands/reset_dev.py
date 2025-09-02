from __future__ import annotations
from typing import Optional
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from main import models as M


class Command(BaseCommand):
    help = "Dangerous: Reset development data (world state) and optionally seed sample data."

    def add_arguments(self, parser):
        parser.add_argument('--yes-i-know', action='store_true', help='Confirm destructive operation')
        parser.add_argument('--seed', action='store_true', help='Seed sample world data after reset')
        parser.add_argument('--wipe-characters', action='store_true', help='Also delete Character rows (does not delete User accounts)')
        parser.add_argument('--wipe-inventory', action='store_true', help='Also delete InventoryItem rows')

    def handle(self, *args, **options):
        if not options.get('yes_i_know'):
            raise CommandError("Refusing to run without --yes-i-know")
        # Local safety: require DEBUG or explicit env opt-in
        allow = bool(getattr(settings, 'DEBUG', False)) or os.environ.get('ALLOW_RESET_DEV') == '1'
        if not allow:
            raise CommandError("reset_dev is only allowed in DEBUG or when ALLOW_RESET_DEV=1 is set")

        self.stdout.write(self.style.WARNING("Resetting development data..."))
        with transaction.atomic():
            # End combats first
            for m in (M.PvECombat, M.PvPCombat):
                try:
                    deleted, _ = m.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted} {m.__name__}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skip {m.__name__}: {e}"))

            # Trades
            for m in (M.TradeItem, M.Trade):
                try:
                    deleted, _ = m.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted} {m.__name__}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skip {m.__name__}: {e}"))

            # Events
            try:
                deleted, _ = M.GameEvent.objects.all().delete()
                self.stdout.write(f"Deleted {deleted} GameEvent")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Skip GameEvent: {e}"))

            # Healing claims / harvests
            for m in (M.HealingClaim, M.ResourceHarvest):
                try:
                    deleted, _ = m.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted} {m.__name__}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skip {m.__name__}: {e}"))

            # Flag-related (children first)
            for m in (M.FlagLedger, M.FlagAttack, M.FlagRun):
                try:
                    deleted, _ = m.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted} {m.__name__}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skip {m.__name__}: {e}"))
            try:
                deleted, _ = M.TerritoryFlag.objects.all().delete()
                self.stdout.write(f"Deleted {deleted} TerritoryFlag")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Skip TerritoryFlag: {e}"))

            # Monsters and resources
            for m in (M.Monster, M.ResourceNode):
                try:
                    deleted, _ = m.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted} {m.__name__}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skip {m.__name__}: {e}"))

            # Optional wipes
            if options.get('wipe_inventory'):
                try:
                    deleted, _ = M.InventoryItem.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted} InventoryItem")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skip InventoryItem: {e}"))
            if options.get('wipe_characters'):
                try:
                    deleted, _ = M.Character.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted} Character")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skip Character: {e}"))

        # Seed sample data
        if options.get('seed'):
            self.stdout.write(self.style.NOTICE("Seeding sample world data..."))
            try:
                # Use helper functions from views to avoid duplication
                from main import views_rpg as V
                V.create_starter_items()
                V.create_monster_templates()
                V.create_basic_regions()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Seed helpers failed: {e}"))
            # Minimal resource nodes near default start
            try:
                gs = getattr(settings, 'GAME_SETTINGS', {})
                lat = float(gs.get('DEFAULT_START_LAT', 41.0646633))
                lon = float(gs.get('DEFAULT_START_LON', -80.6391736))
                # simple scatter
                def mk(lat_off: float, lon_off: float, t: str, qty: int = 5):
                    return M.ResourceNode.objects.create(
                        resource_type=t, lat=lat + lat_off, lon=lon + lon_off,
                        level=1, quantity=qty, max_quantity=max(qty, 5), respawn_time=45
                    )
                mk(0.0002, 0.0000, 'berry_bush', 5)
                mk(-0.0002, 0.0001, 'tree', 5)
                mk(0.0001, -0.0002, 'stone_quarry', 5)
                self.stdout.write("Seeded a few nearby resources")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to seed resources: {e}"))

        self.stdout.write(self.style.SUCCESS("reset_dev completed."))

