from django.core.management.base import BaseCommand
from main.models import Character, ItemTemplate, InventoryItem
from django.db import transaction

class Command(BaseCommand):
    help = 'Give resources to a player for testing'

    def add_arguments(self, parser):
        parser.add_argument('player_name', type=str, help='Name of the player character')
        parser.add_argument('resource', type=str, help='Resource name (e.g., wood, stone, gold)')
        parser.add_argument('amount', type=int, help='Amount to give')

    def handle(self, *args, **options):
        player_name = options['player_name']
        resource = options['resource']
        amount = options['amount']
        
        try:
            with transaction.atomic():
                # Find the character
                try:
                    character = Character.objects.get(name__iexact=player_name)
                    self.stdout.write(f"Found character: {character.name}")
                except Character.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"Character '{player_name}' not found!")
                    )
                    # Show available characters
                    characters = Character.objects.all()
                    if characters:
                        self.stdout.write("Available characters:")
                        for char in characters:
                            self.stdout.write(f"  - {char.name}")
                    return

                # Handle gold differently (it's stored directly on character)
                if resource.lower() == 'gold':
                    old_gold = character.gold
                    character.gold += amount
                    character.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Gave {amount:,} gold to {character.name}! "
                            f"({old_gold:,} → {character.gold:,})"
                        )
                    )
                    return

                # For other resources, handle inventory items
                try:
                    # Get or create the item template
                    item_template, created = ItemTemplate.objects.get_or_create(
                        name=resource,
                        defaults={
                            'description': f'{resource.title()} resource',
                            'item_type': 'resource',
                            'max_stack': 9999999,  # Large stack size for resources
                            'value': 1,
                            'weight': 0.1,
                            'is_consumable': False,
                            'is_stackable': True
                        }
                    )
                    
                    if created:
                        self.stdout.write(f"Created new item template: {resource}")

                    # Get or create the inventory item
                    inventory_item, created = InventoryItem.objects.get_or_create(
                        character=character,
                        item_template=item_template,
                        defaults={'quantity': 0}
                    )
                    
                    old_quantity = inventory_item.quantity
                    inventory_item.quantity += amount
                    inventory_item.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Gave {amount:,}x {resource} to {character.name}! "
                            f"({old_quantity:,} → {inventory_item.quantity:,})"
                        )
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error giving {resource}: {e}")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Unexpected error: {e}")
            )
