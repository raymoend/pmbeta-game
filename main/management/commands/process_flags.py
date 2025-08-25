from django.core.management.base import BaseCommand
from django.utils import timezone
from time import sleep

from main.services.flags import process_flags_tick
from main.services.territory import spawn_monsters_for_groups

class Command(BaseCommand):
    help = "Accrue income and apply upkeep for flags"

    def add_arguments(self, parser):
        parser.add_argument("--tick", action="store_true", help="Run a single tick")
        parser.add_argument("--loop", action="store_true", help="Run forever with interval seconds")
        parser.add_argument("--interval", type=int, default=60, help="Seconds between ticks in --loop")
        parser.add_argument("--spawn-territory-npcs", action="store_true", help="Also spawn NPCs in territory circles each tick")

    def handle(self, *args, **options):
        loop = options["loop"]
        tick = options["tick"] or not loop
        interval = options["interval"]
        do_spawn = options.get("spawn_territory_npcs", False)
        if loop:
            self.stdout.write(self.style.SUCCESS("Starting flag processor loop"))
            while True:
                process_flags_tick(now=timezone.now())
                if do_spawn:
                    spawned = spawn_monsters_for_groups()
                    self.stdout.write(f"Spawned {spawned} territory NPCs")
                sleep(interval)
        elif tick:
            process_flags_tick(now=timezone.now())
            if do_spawn:
                spawned = spawn_monsters_for_groups()
                self.stdout.write(f"Spawned {spawned} territory NPCs")
            self.stdout.write(self.style.SUCCESS("Processed one tick"))

