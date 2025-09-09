"""
Ensure NPC loot: create item templates and set drop pools per NPC mapping.
Usage:
  python manage.py ensure_npc_loot
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Seed item templates for NPC loot and update MonsterTemplate drop pools per design'

    def handle(self, *args, **options):
        from django.db.models import Q
        from main.models import ItemTemplate, MonsterTemplate

        # Define item templates with sensible defaults
        # item_type: weapon|armor|consumable|material|quest|misc
        ITEMS = {
            # Yakuza Blade
            'Steel Blades':        dict(description='Forged steel components for fine blades', item_type='material', rarity='common', base_value=20, max_stack_size=50),
            'Honor Tokens':        dict(description='Marks of honor used in syndicate dealings', item_type='misc', rarity='uncommon', base_value=15, max_stack_size=50),
            'Katana Blueprint':    dict(description='A rare blueprint for crafting a katana', item_type='quest', rarity='rare', base_value=200, max_stack_size=1),
            # Cartel Sicario
            'Bullet Casings':      dict(description='Spent casings reused for ammo crafting', item_type='material', rarity='common', base_value=8, max_stack_size=100),
            'Smuggled Goods':      dict(description='Contraband items with trade value', item_type='misc', rarity='uncommon', base_value=50, max_stack_size=20),
            'Drug Cache':          dict(description='Illicit stimulants that restore stamina', item_type='consumable', rarity='rare', base_value=120, max_stack_size=5, stamina_restore=100),
            # Void Cultist
            'Eldritch Runes':      dict(description='Occult inscriptions used in rituals', item_type='material', rarity='uncommon', base_value=30, max_stack_size=25),
            'Dark Essence':        dict(description='Condensed void energy', item_type='material', rarity='uncommon', base_value=40, max_stack_size=25),
            'Void Artifact':       dict(description='Ancient relic pulsing with void power', item_type='material', rarity='epic', base_value=300, max_stack_size=5),
            # Drone Marauder
            'Circuit Boards':      dict(description='Electronic boards harvested from drones', item_type='material', rarity='common', base_value=18, max_stack_size=50),
            'Energy Cells':        dict(description='High-density power cells for tech gear', item_type='material', rarity='uncommon', base_value=35, max_stack_size=25),
            'AI Core':             dict(description='Sophisticated AI core for advanced devices', item_type='material', rarity='rare', base_value=250, max_stack_size=5),
            # Cave Bear
            'Bear Pelts':          dict(description='Thick pelts from cave bears', item_type='material', rarity='common', base_value=22, max_stack_size=50),
            'Claws':               dict(description='Sharp animal claws used in crafting', item_type='material', rarity='common', base_value=10, max_stack_size=50),
            'Ancient Bone Relic':  dict(description='Old bone relic with mysterious markings', item_type='material', rarity='rare', base_value=180, max_stack_size=5),
            # Alien Stalker
            'Xenotech Scraps':     dict(description='Fragments of alien technology', item_type='material', rarity='uncommon', base_value=28, max_stack_size=50),
            'Bio-Samples':         dict(description='Alien biological samples for research', item_type='material', rarity='uncommon', base_value=24, max_stack_size=50),
            'Plasma Emitter':      dict(description='Experimental alien plasma component', item_type='material', rarity='rare', base_value=260, max_stack_size=5),
            # Mafia Enforcer
            'Gold Chains':         dict(description='Heavy gold chain jewelry', item_type='misc', rarity='uncommon', base_value=60, max_stack_size=10),
            'Protection Rackets':  dict(description='Records of dues from protection schemes', item_type='misc', rarity='uncommon', base_value=45, max_stack_size=20),
            'Mob Contract':        dict(description='Signed contract binding underworld terms', item_type='quest', rarity='rare', base_value=220, max_stack_size=1),
            # Forest Wolf
            'Wolf Furs':           dict(description='Warm furs from wolves', item_type='material', rarity='common', base_value=12, max_stack_size=50),
            'Teeth':               dict(description='Animal teeth used in trinkets', item_type='material', rarity='common', base_value=6, max_stack_size=100),
            'Alpha Scent Gland':   dict(description='Gland used for stealth gear crafting', item_type='material', rarity='rare', base_value=140, max_stack_size=5),
            # Rabbit
            'Rabbit Meat':         dict(description='Fresh meat for basic meals', item_type='consumable', rarity='common', base_value=5, max_stack_size=20, heal_amount=10),
            'Hides':               dict(description='Small hides for beginner crafting', item_type='material', rarity='common', base_value=8, max_stack_size=50),
            'Lucky Foot Charm':    dict(description='A charm said to bring luck', item_type='misc', rarity='rare', base_value=90, max_stack_size=5),
            # Goblin Scout
            'Goblin Tools':        dict(description='Crude tools used by goblins', item_type='material', rarity='common', base_value=10, max_stack_size=50),
            'Mushrooms':           dict(description='Edible fungi; minor restorative', item_type='consumable', rarity='common', base_value=4, max_stack_size=20, heal_amount=5),
            'Scout Map Fragment':  dict(description='Fragment of a map revealing secrets', item_type='quest', rarity='rare', base_value=110, max_stack_size=5),
        }

        # Ensure item templates
        created, updated = 0, 0
        for name, data in ITEMS.items():
            obj, was_created = ItemTemplate.objects.get_or_create(name=name, defaults=data)
            if was_created:
                created += 1
            else:
                # Keep existing values; only fill in missing stacks or economic fields if zero
                changed = False
                for k, v in data.items():
                    cur = getattr(obj, k, None)
                    if cur in (None, 0, '') and v not in (None, 0, ''):
                        setattr(obj, k, v)
                        changed = True
                if changed:
                    obj.save()
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f"ItemTemplates ensured: created={created}, updated={updated}"))

        # Define NPC drop tables with probabilities
        DROPS = {
            'Yakuza Blade': {
                'commons': [('Steel Blades', 0.75), ('Honor Tokens', 0.60)],
                'rares':   [('Katana Blueprint', 0.10)],
            },
            'Cartel Sicario': {
                'commons': [('Bullet Casings', 0.75), ('Smuggled Goods', 0.50)],
                'rares':   [('Drug Cache', 0.15)],
            },
            'Void Cultist': {
                'commons': [('Eldritch Runes', 0.65), ('Dark Essence', 0.55)],
                'rares':   [('Void Artifact', 0.12)],
            },
            'Drone Marauder': {
                'commons': [('Circuit Boards', 0.70), ('Energy Cells', 0.60)],
                'rares':   [('AI Core', 0.12)],
            },
            'Cave Bear': {
                'commons': [('Bear Pelts', 0.75), ('Claws', 0.65)],
                'rares':   [('Ancient Bone Relic', 0.12)],
            },
            'Alien Stalker': {
                'commons': [('Xenotech Scraps', 0.70), ('Bio-Samples', 0.50)],
                'rares':   [('Plasma Emitter', 0.10)],
            },
            'Mafia Enforcer': {
                'commons': [('Gold Chains', 0.75), ('Protection Rackets', 0.60)],
                'rares':   [('Mob Contract', 0.12)],
            },
            'Forest Wolf': {
                'commons': [('Wolf Furs', 0.80), ('Teeth', 0.70)],
                'rares':   [('Alpha Scent Gland', 0.12)],
            },
            'Rabbit': {
                'commons': [('Rabbit Meat', 0.80), ('Hides', 0.70)],
                'rares':   [('Lucky Foot Charm', 0.08)],
            },
            'Goblin Scout': {
                'commons': [('Goblin Tools', 0.70), ('Mushrooms', 0.60)],
                'rares':   [('Scout Map Fragment', 0.10)],
            },
        }

        # Update MonsterTemplate.drop_pool accordingly
        updated_templates = 0
        for tmpl in MonsterTemplate.objects.filter(name__in=list(DROPS.keys())):
            spec = DROPS.get(tmpl.name)
            pool = []
            for nm, pr in spec.get('commons', []):
                pool.append({'item': nm, 'quantity': 1, 'prob': float(pr)})
            for nm, pr in spec.get('rares', []):
                pool.append({'item': nm, 'quantity': 1, 'prob': float(pr)})
            tmpl.drop_pool = pool
            tmpl.save(update_fields=['drop_pool', 'updated_at'])
            updated_templates += 1

        self.stdout.write(self.style.SUCCESS(f"Updated drop pools on {updated_templates} MonsterTemplates"))

