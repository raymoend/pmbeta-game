"""
Create basic crafting recipes for the game
This populates the crafting system with useful recipes using collected resources
"""
from django.core.management.base import BaseCommand
from main.models import CraftingRecipe, CraftingRecipeMaterial, ItemTemplate


class Command(BaseCommand):
    help = 'Create basic crafting recipes using collected resources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing recipes before creating new ones'
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted_recipes = CraftingRecipe.objects.all().delete()[0]
            self.stdout.write(f"Deleted {deleted_recipes} existing recipes")

        # Define recipes with their required materials
        recipes_data = [
            # TOOLS CATEGORY
            {
                'name': 'Stone Axe',
                'description': 'A basic axe for chopping wood more efficiently',
                'category': 'tools',
                'result_item_data': {
                    'name': 'Stone Axe',
                    'description': 'Increases wood gathering efficiency by 50%',
                    'item_type': 'weapon',
                    'damage': 8,
                    'base_value': 25,
                },
                'materials': [
                    {'name': 'wood', 'quantity': 2},
                    {'name': 'stone', 'quantity': 3},
                ],
                'required_level': 3,
                'craft_time': 15,
                'experience_reward': 30,
            },
            {
                'name': 'Iron Pickaxe',
                'description': 'Mining tool that increases ore gathering efficiency',
                'category': 'tools',
                'result_item_data': {
                    'name': 'Iron Pickaxe',
                    'description': 'Increases mining efficiency by 75%',
                    'item_type': 'weapon',
                    'damage': 12,
                    'base_value': 50,
                },
                'materials': [
                    {'name': 'wood', 'quantity': 2},
                    {'name': 'iron_ore', 'quantity': 4},
                ],
                'required_level': 5,
                'required_skill_level': 3,
                'craft_time': 25,
                'experience_reward': 50,
            },
            
            # WEAPONS CATEGORY
            {
                'name': 'Wooden Spear',
                'description': 'Basic weapon for combat',
                'category': 'weapons',
                'result_item_data': {
                    'name': 'Wooden Spear',
                    'description': 'A simple but effective weapon',
                    'item_type': 'weapon',
                    'damage': 15,
                    'base_value': 20,
                },
                'materials': [
                    {'name': 'wood', 'quantity': 3},
                    {'name': 'stone', 'quantity': 1},
                ],
                'required_level': 2,
                'craft_time': 10,
                'experience_reward': 25,
            },
            {
                'name': 'Iron Sword',
                'description': 'Sharp iron blade for experienced warriors',
                'category': 'weapons',
                'result_item_data': {
                    'name': 'Iron Sword',
                    'description': 'A well-balanced iron sword',
                    'item_type': 'weapon',
                    'damage': 25,
                    'strength_bonus': 3,
                    'base_value': 75,
                    'rarity': 'uncommon',
                },
                'materials': [
                    {'name': 'iron_ore', 'quantity': 5},
                    {'name': 'wood', 'quantity': 1},
                ],
                'required_level': 8,
                'required_skill_level': 4,
                'craft_time': 30,
                'experience_reward': 75,
                'base_success_rate': 0.7,
            },
            
            # ARMOR CATEGORY
            {
                'name': 'Leather Vest',
                'description': 'Basic protection from animal hides',
                'category': 'armor',
                'result_item_data': {
                    'name': 'Leather Vest',
                    'description': 'Provides basic protection',
                    'item_type': 'armor',
                    'defense_bonus': 5,
                    'vitality_bonus': 2,
                    'base_value': 30,
                },
                'materials': [
                    {'name': 'food', 'quantity': 4},  # Representing animal hides
                ],
                'required_level': 4,
                'required_skill_level': 2,
                'craft_time': 20,
                'experience_reward': 40,
            },
            
            # CONSUMABLES CATEGORY
            {
                'name': 'Health Potion',
                'description': 'Restore health using berries and herbs',
                'category': 'consumables',
                'result_item_data': {
                    'name': 'Health Potion',
                    'description': 'Restores 50% of maximum health',
                    'item_type': 'consumable',
                    'heal_percentage': 0.5,
                    'base_value': 25,
                    'max_stack_size': 5,
                },
                'materials': [
                    {'name': 'berries', 'quantity': 3},
                    {'name': 'food', 'quantity': 1},  # Herbs/water
                ],
                'required_level': 3,
                'required_skill_level': 2,
                'craft_time': 8,
                'experience_reward': 20,
                'result_quantity': 2,
            },
            {
                'name': 'Energy Tonic',
                'description': 'Restore stamina using natural ingredients',
                'category': 'consumables',
                'result_item_data': {
                    'name': 'Energy Tonic',
                    'description': 'Restores 75 stamina points',
                    'item_type': 'consumable',
                    'stamina_restore': 75,
                    'base_value': 20,
                    'max_stack_size': 8,
                },
                'materials': [
                    {'name': 'berries', 'quantity': 2},
                    {'name': 'food', 'quantity': 2},
                ],
                'required_level': 2,
                'craft_time': 5,
                'experience_reward': 15,
                'result_quantity': 3,
            },
            
            # MATERIALS CATEGORY
            {
                'name': 'Iron Ingot',
                'description': 'Process raw ore into refined metal',
                'category': 'materials',
                'result_item_data': {
                    'name': 'Iron Ingot',
                    'description': 'Refined iron ready for advanced crafting',
                    'item_type': 'material',
                    'base_value': 15,
                    'max_stack_size': 20,
                    'rarity': 'uncommon',
                },
                'materials': [
                    {'name': 'iron_ore', 'quantity': 3},
                    {'name': 'wood', 'quantity': 1},  # Fuel for smelting
                ],
                'required_level': 6,
                'required_skill_level': 3,
                'craft_time': 20,
                'experience_reward': 35,
                'result_quantity': 2,
            },
            {
                'name': 'Reinforced Wood',
                'description': 'Treat wood with stone dust for durability',
                'category': 'materials',
                'result_item_data': {
                    'name': 'Reinforced Wood',
                    'description': 'Enhanced wood for better construction',
                    'item_type': 'material',
                    'base_value': 8,
                    'max_stack_size': 25,
                },
                'materials': [
                    {'name': 'wood', 'quantity': 2},
                    {'name': 'stone', 'quantity': 1},
                ],
                'required_level': 2,
                'craft_time': 12,
                'experience_reward': 20,
                'result_quantity': 3,
            },
            # NEW: Drug Cache Synthesis (Cartel consumable)
            {
                'name': 'Drug Cache Synthesis',
                'description': 'Refine contraband and power cells into a potent stamina booster',
                'category': 'consumables',
                'result_item_data': {
                    'name': 'Drug Cache',
                    'description': 'Illicit stimulants that restore stamina',
                    'item_type': 'consumable',
                    'stamina_restore': 100,
                    'base_value': 120,
                    'max_stack_size': 5,
                    'rarity': 'rare',
                },
                'materials': [
                    {'name': 'Smuggled Goods', 'quantity': 1},
                    {'name': 'Energy Cells', 'quantity': 1},
                    {'name': 'Bullet Casings', 'quantity': 5},
                ],
                'required_level': 7,
                'required_skill_level': 4,
                'craft_time': 20,
                'experience_reward': 60,
                'base_success_rate': 0.65,
                'result_quantity': 1,
            },
            # NEW: Cooked Rations (basic heal from Rabbit + Mushroom)
            {
                'name': 'Cooked Rations',
                'description': 'Cook a simple ration from meat and mushrooms',
                'category': 'consumables',
                'result_item_data': {
                    'name': 'Cooked Rations',
                    'description': 'Hearty ration that restores 25 HP',
                    'item_type': 'consumable',
                    'heal_amount': 25,
                    'base_value': 18,
                    'max_stack_size': 10,
                    'rarity': 'common',
                },
                'materials': [
                    {'name': 'Rabbit Meat', 'quantity': 1},
                    {'name': 'Mushrooms', 'quantity': 1},
                ],
                'required_level': 2,
                'required_skill_level': 1,
                'craft_time': 6,
                'experience_reward': 12,
                'base_success_rate': 0.85,
                'result_quantity': 2,
            },
            # NEW: Ammo Pack (damage boost buff consumable)
            {
                'name': 'Ammo Pack',
                'description': 'Ammunition pack that boosts weapon damage for a short time',
                'category': 'consumables',
                'result_item_data': {
                    'name': 'Ammo Pack',
                    'description': 'Boosts weapon damage for 15 seconds',
                    'item_type': 'consumable',
                    'base_value': 60,
                    'max_stack_size': 10,
                    'rarity': 'uncommon',
                },
                'materials': [
                    {'name': 'Bullet Casings', 'quantity': 10},
                    {'name': 'Energy Cells', 'quantity': 1},
                ],
                'required_level': 4,
                'required_skill_level': 2,
                'craft_time': 8,
                'experience_reward': 18,
                'base_success_rate': 0.8,
                'result_quantity': 2,
            },
            # NEW: Void Tonic (mana-focused)
            {
                'name': 'Void Tonic',
                'description': 'A tonic distilled from void materials that restores mana',
                'category': 'consumables',
                'result_item_data': {
                    'name': 'Void Tonic',
                    'description': 'Restores 60 mana',
                    'item_type': 'consumable',
                    'mana_restore': 60,
                    'base_value': 70,
                    'max_stack_size': 5,
                    'rarity': 'uncommon',
                },
                'materials': [
                    {'name': 'Dark Essence', 'quantity': 1},
                    {'name': 'Eldritch Runes', 'quantity': 1},
                ],
                'required_level': 5,
                'required_skill_level': 3,
                'craft_time': 10,
                'experience_reward': 28,
                'base_success_rate': 0.78,
                'result_quantity': 1,
            },
        ]

        created_recipes = []
        
        for recipe_data in recipes_data:
            # Create or get the result item template
            result_item_data = recipe_data['result_item_data']
            result_item, created = ItemTemplate.objects.get_or_create(
                name=result_item_data['name'],
                defaults=result_item_data
            )
            
            if created:
                self.stdout.write(f"Created item template: {result_item.name}")

            # Create the recipe
            recipe = CraftingRecipe.objects.create(
                name=recipe_data['name'],
                description=recipe_data['description'],
                category=recipe_data['category'],
                result_item=result_item,
                result_quantity=recipe_data.get('result_quantity', 1),
                required_level=recipe_data.get('required_level', 1),
                required_skill_level=recipe_data.get('required_skill_level', 1),
                base_success_rate=recipe_data.get('base_success_rate', 0.8),
                craft_time_seconds=recipe_data.get('craft_time', 10),
                experience_reward=recipe_data.get('experience_reward', 25),
            )

            # Add required materials
            for material_data in recipe_data['materials']:
                CraftingRecipeMaterial.objects.create(
                    recipe=recipe,
                    material_name=material_data['name'],
                    quantity_required=material_data['quantity']
                )

            created_recipes.append({
                'name': recipe.name,
                'category': recipe.category,
                'materials': len(recipe_data['materials']),
                'level_req': recipe.required_level,
                'result': result_item.name
            })

        self.stdout.write(
            self.style.SUCCESS(f'Created {len(created_recipes)} crafting recipes!')
        )

        # Show summary by category
        category_summary = {}
        for recipe in created_recipes:
            cat = recipe['category']
            if cat not in category_summary:
                category_summary[cat] = 0
            category_summary[cat] += 1

        self.stdout.write("\nRecipes by Category:")
        for category, count in category_summary.items():
            self.stdout.write(f"  {category.title()}: {count}")

        # Show examples
        self.stdout.write("\nExample Recipes Created:")
        for recipe in created_recipes[:5]:
            self.stdout.write(
                f"  {recipe['name']} (Lv.{recipe['level_req']}) - "
                f"{recipe['materials']} materials -> {recipe['result']}"
            )
        
        if len(created_recipes) > 5:
            self.stdout.write(f"  ... and {len(created_recipes) - 5} more")

        self.stdout.write(
            self.style.SUCCESS(
                "\nCrafting system ready! Players can now combine resources to create "
                "tools, weapons, armor, potions, and refined materials."
            )
        )
