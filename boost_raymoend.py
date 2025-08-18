#!/usr/bin/env python3
"""
Boost Raymoend Character Script
Boosts existing character "raymoend" to maximum level and resources for testing
"""
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from django.contrib.auth.models import User
from main.models import Character, Skill, ItemTemplate, InventoryItem
from django.conf import settings
from django.db import transaction

def boost_raymoend():
    """Boost raymoend character to max stats and resources"""
    
    print("🚀 Boosting Raymoend Character to Max Stats for Testing...")
    print("=" * 60)
    
    try:
        with transaction.atomic():
            # Find the raymoend character (case insensitive)
            try:
                character = Character.objects.get(name__iexact="raymoend")
                print(f"✓ Found character: {character.name}")
                print(f"  Current Level: {character.level}")
                print(f"  Current Gold: {character.gold:,}")
            except Character.DoesNotExist:
                print("❌ Character 'raymoend' not found!")
                print("Available characters:")
                characters = Character.objects.all()
                if characters:
                    for char in characters:
                        print(f"  - {char.name} (Level {char.level}) - User: {char.user.username}")
                else:
                    print("  No characters found in database")
                return False
            
            # Store original stats for comparison
            original_level = character.level
            original_gold = character.gold
            original_hp = character.current_hp
            
            # BOOST TO MAX STATS
            print(f"\n→ Boosting {character.name} to maximum stats...")
            
            # MAX LEVEL AND STATS
            character.level = 100  # Maximum level
            character.experience = 0  # Start fresh at max level
            
            # MAX CORE ATTRIBUTES
            character.strength = 500      # Max physical power
            character.defense = 500       # Max defense
            character.vitality = 500      # Max health/stamina
            character.agility = 500       # Max speed/dodge
            character.intelligence = 500  # Max magic power
            
            # MAX RESOURCES
            character.gold = 999999999    # Nearly unlimited gold
            
            # Recalculate derived stats based on new attributes
            character.recalculate_derived_stats()
            character.current_hp = character.max_hp
            character.current_mana = character.max_mana
            character.current_stamina = character.max_stamina
            
            # Set status
            character.is_online = True
            character.in_combat = False
            character.pvp_enabled = True
            
            character.save()
            
            print(f"✓ Character boosted!")
            print(f"  → Level: {original_level} → {character.level}")
            print(f"  → Strength: {character.strength}")
            print(f"  → Defense: {character.defense}")
            print(f"  → Vitality: {character.vitality}")
            print(f"  → Agility: {character.agility}")
            print(f"  → Intelligence: {character.intelligence}")
            print(f"  → Gold: {original_gold:,} → {character.gold:,}")
            print(f"  → HP: {original_hp} → {character.current_hp}/{character.max_hp}")
            print(f"  → Mana: {character.current_mana}/{character.max_mana}")
            print(f"  → Stamina: {character.current_stamina}/{character.max_stamina}")
            
            # BOOST ALL SKILLS TO MAX LEVEL
            print("\n→ Boosting all skills to maximum level...")
            
            # Get existing skills
            existing_skills = {skill.name: skill for skill in character.skills.all()}
            
            # Define all possible skills
            all_skills = [
                ('Combat', 'combat'),
                ('Magic', 'magic'),
                ('Crafting', 'crafting'),
                ('Gathering', 'gathering'),
                ('Social', 'social'),
            ]
            
            for skill_name, skill_type in all_skills:
                if skill_name in existing_skills:
                    # Update existing skill
                    skill = existing_skills[skill_name]
                    old_level = skill.level
                    skill.level = 100
                    skill.experience = 0
                    skill.save()
                    print(f"  ✓ Updated {skill_name}: Level {old_level} → 100")
                else:
                    # Create new skill
                    skill = Skill.objects.create(
                        character=character,
                        name=skill_name,
                        skill_type=skill_type,
                        level=100,
                        experience=0
                    )
                    print(f"  ✓ Created {skill_name} skill at level 100")
            
            # ADD ITEMS TO INVENTORY
            print("\n→ Adding items to inventory...")
            
            # Items to add (item_name, quantity)
            items_to_add = [
                # Weapons
                ('Rusty Sword', 1),
                ('Iron Sword', 5),
                
                # Armor  
                ('Leather Vest', 1),
                ('Chain Mail', 3),
                
                # Consumables
                ('Health Potion', 99),  # More consumables
                ('Mana Potion', 99),
                
                # Resources
                ('wood', 200),      # Double resources
                ('stone', 200),
                ('food', 150),
                ('berries', 150),
                ('iron_ore', 100),
                ('gold_ore', 100),
                ('ancient_artifact', 25),
            ]
            
            for item_name, quantity in items_to_add:
                try:
                    # Check if item already exists in inventory
                    try:
                        item_template = ItemTemplate.objects.get(name=item_name)
                        inventory_item, created = InventoryItem.objects.get_or_create(
                            character=character,
                            item_template=item_template,
                            defaults={'quantity': 0}
                        )
                        old_quantity = inventory_item.quantity
                        inventory_item.quantity = max(inventory_item.quantity, quantity)
                        inventory_item.save()
                        
                        if created:
                            print(f"  ✓ Added {quantity}x {item_name}")
                        else:
                            print(f"  ✓ Updated {item_name}: {old_quantity}x → {inventory_item.quantity}x")
                            
                    except ItemTemplate.DoesNotExist:
                        # Create via character method if template doesn't exist
                        inventory_item = character.add_item_to_inventory(item_name, quantity)
                        print(f"  ✓ Added {quantity}x {item_name} (created template)")
                        
                except Exception as e:
                    print(f"  ⚠ Failed to add {item_name}: {e}")
            
            print("\n" + "=" * 60)
            print("🎉 RAYMOEND CHARACTER BOOSTED SUCCESSFULLY!")
            print("=" * 60)
            print(f"🎮 {character.name} is now a MAXED character:")
            print(f"   Level: {character.level} (MAX)")
            print(f"   All Attributes: 500 (MAX)")
            print(f"   Gold: {character.gold:,}")
            print(f"   HP/Mana/Stamina: ALL MAXED")
            print(f"   All Skills: Level 100 (MAX)")
            print(f"   Location: {character.lat:.6f}, {character.lon:.6f}")
            print("\n📦 Inventory: Loaded with weapons, armor, consumables, and resources")
            print(f"\n🔑 Login as: {character.user.username}")
            print("🚀 Ready for Testing!")
            
    except Exception as e:
        print(f"❌ Error boosting character: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def show_all_characters():
    """Show all characters in the database"""
    print("\n📊 All Characters in Database:")
    print("=" * 50)
    
    characters = Character.objects.all().select_related('user')
    
    if not characters:
        print("No characters found.")
        return
    
    for char in characters:
        print(f"Character: {char.name}")
        print(f"  User: {char.user.username}")
        print(f"  Level: {char.level}")
        print(f"  Gold: {char.gold:,}")
        print(f"  HP: {char.current_hp}/{char.max_hp}")
        print(f"  Location: {char.lat:.6f}, {char.lon:.6f}")
        print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        show_all_characters()
    else:
        success = boost_raymoend()
        if success:
            print("\n" + "🌟" * 20)
            print("RAYMOEND READY TO DOMINATE!")
            print("🌟" * 20)
