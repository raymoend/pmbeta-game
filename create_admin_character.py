#!/usr/bin/env python3
"""
Create Admin Character Script
Creates an admin user with maximum level and resources for testing purposes
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

def create_admin_character():
    """Create admin user with maxed out character for testing"""
    
    print("🚀 Creating Admin Character with Max Stats for Testing...")
    print("=" * 60)
    
    # Admin user credentials
    admin_username = "admin"
    admin_password = "admin123"
    admin_email = "admin@theshatteredrealm.com"
    character_name = "AdminTest"
    
    try:
        with transaction.atomic():
            # Create or get superuser
            admin_user, created = User.objects.get_or_create(
                username=admin_username,
                defaults={
                    'email': admin_email,
                    'is_superuser': True,
                    'is_staff': True,
                    'is_active': True
                }
            )
            
            if created:
                admin_user.set_password(admin_password)
                admin_user.save()
                print(f"✓ Created superuser: {admin_username}")
            else:
                print(f"→ Superuser already exists: {admin_username}")
            
            # Delete existing admin character if exists
            try:
                existing_character = Character.objects.get(user=admin_user)
                print(f"→ Deleting existing character: {existing_character.name}")
                existing_character.delete()
            except Character.DoesNotExist:
                pass
            
            # Get default start location
            try:
                start_lat = settings.GAME_SETTINGS.get('DEFAULT_START_LAT', 41.0646633)
                start_lon = settings.GAME_SETTINGS.get('DEFAULT_START_LON', -80.6391736)
            except AttributeError:
                start_lat = 41.0646633  # Cleveland area
                start_lon = -80.6391736
            
            # Create admin character with MAX STATS
            print(f"→ Creating character: {character_name}")
            character = Character.objects.create(
                user=admin_user,
                name=character_name,
                lat=start_lat,
                lon=start_lon,
                
                # MAX LEVEL AND STATS
                level=100,  # Maximum level
                experience=0,  # Start fresh at max level
                
                # MAX CORE ATTRIBUTES
                strength=500,      # Max physical power
                defense=500,       # Max defense
                vitality=500,      # Max health/stamina
                agility=500,       # Max speed/dodge
                intelligence=500,  # Max magic power
                
                # MAX RESOURCES
                gold=999999999,    # Nearly unlimited gold
                
                # FULL HEALTH/MANA/STAMINA (will be recalculated)
                current_hp=1,
                current_mana=1,
                current_stamina=1,
                
                # STATUS
                is_online=True,
                in_combat=False,
                pvp_enabled=True
            )
            
            # Recalculate derived stats based on attributes
            character.recalculate_derived_stats()
            character.current_hp = character.max_hp
            character.current_mana = character.max_mana
            character.current_stamina = character.max_stamina
            character.save()
            
            print(f"✓ Character created with stats:")
            print(f"  → Level: {character.level}")
            print(f"  → Strength: {character.strength}")
            print(f"  → Defense: {character.defense}")
            print(f"  → Vitality: {character.vitality}")
            print(f"  → Agility: {character.agility}")
            print(f"  → Intelligence: {character.intelligence}")
            print(f"  → Gold: {character.gold:,}")
            print(f"  → HP: {character.current_hp}/{character.max_hp}")
            print(f"  → Mana: {character.current_mana}/{character.max_mana}")
            print(f"  → Stamina: {character.current_stamina}/{character.max_stamina}")
            
            # Create MAX LEVEL SKILLS
            max_skills = [
                ('Combat', 'combat'),
                ('Magic', 'magic'),
                ('Crafting', 'crafting'),
                ('Gathering', 'gathering'),
                ('Social', 'social'),
            ]
            
            print("→ Creating maxed skills...")
            for skill_name, skill_type in max_skills:
                skill, created = Skill.objects.get_or_create(
                    character=character,
                    name=skill_name,
                    defaults={
                        'skill_type': skill_type,
                        'level': 100,  # Max skill level
                        'experience': 0
                    }
                )
                if created:
                    print(f"  ✓ Created {skill_name} skill at level 100")
                else:
                    skill.level = 100
                    skill.experience = 0
                    skill.save()
                    print(f"  ✓ Updated {skill_name} skill to level 100")
            
            # Add starter items and resources to inventory
            print("→ Adding starter items and resources...")
            starter_items = [
                # Weapons
                ('Rusty Sword', 1),
                ('Iron Sword', 5),
                
                # Armor  
                ('Leather Vest', 1),
                ('Chain Mail', 3),
                
                # Consumables
                ('Health Potion', 50),
                ('Mana Potion', 50),
                
                # Resources (using the template creation from models)
                ('wood', 100),
                ('stone', 100),
                ('food', 100),
                ('berries', 100),
                ('iron_ore', 50),
                ('gold_ore', 50),
                ('ancient_artifact', 10),
            ]
            
            for item_name, quantity in starter_items:
                try:
                    # Try to add the item (will create template if needed)
                    inventory_item = character.add_item_to_inventory(item_name, quantity)
                    print(f"  ✓ Added {quantity}x {item_name}")
                except Exception as e:
                    print(f"  ⚠ Failed to add {item_name}: {e}")
            
            print("\n" + "=" * 60)
            print("🎉 ADMIN CHARACTER CREATED SUCCESSFULLY!")
            print("=" * 60)
            print(f"🔑 Login Credentials:")
            print(f"   Username: {admin_username}")
            print(f"   Password: {admin_password}")
            print(f"   Character: {character_name}")
            print("\n🎮 Character Stats:")
            print(f"   Level: {character.level} (MAX)")
            print(f"   All Attributes: 500 (MAX)")
            print(f"   Gold: {character.gold:,}")
            print(f"   HP/Mana/Stamina: ALL MAXED")
            print(f"   All Skills: Level 100 (MAX)")
            print(f"   Location: {character.lat:.6f}, {character.lon:.6f}")
            print("\n📦 Inventory: Loaded with weapons, armor, consumables, and resources")
            print("\n🚀 Ready for Testing!")
            print("   1. Start server: python manage.py runserver")
            print("   2. Visit: http://127.0.0.1:8000/")
            print(f"   3. Login with {admin_username}/{admin_password}")
            print("   4. Navigate to game and dominate! 💪")
            
    except Exception as e:
        print(f"❌ Error creating admin character: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def show_character_info():
    """Show existing admin character info"""
    try:
        admin_user = User.objects.get(username='admin')
        character = Character.objects.get(user=admin_user)
        
        print("\n📊 Current Admin Character Stats:")
        print("=" * 40)
        print(f"Character: {character.name}")
        print(f"Level: {character.level}")
        print(f"Strength: {character.strength}")
        print(f"Defense: {character.defense}")
        print(f"Vitality: {character.vitality}")
        print(f"Agility: {character.agility}")
        print(f"Intelligence: {character.intelligence}")
        print(f"Gold: {character.gold:,}")
        print(f"HP: {character.current_hp}/{character.max_hp}")
        print(f"Mana: {character.current_mana}/{character.max_mana}")
        print(f"Stamina: {character.current_stamina}/{character.max_stamina}")
        
        # Show skills
        skills = character.skills.all()
        if skills:
            print("\nSkills:")
            for skill in skills:
                print(f"  {skill.name}: Level {skill.level}")
        
        # Show inventory summary
        inventory = character.get_inventory_summary()
        if inventory:
            print(f"\nInventory ({len(inventory)} item types):")
            for item_name, item_data in inventory.items():
                print(f"  {item_name}: {item_data['quantity']}x")
        
    except (User.DoesNotExist, Character.DoesNotExist):
        print("❌ No admin character found. Run the script to create one.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'info':
        show_character_info()
    else:
        success = create_admin_character()
        if success:
            print("\n" + "🌟" * 20)
            print("ADMIN CHARACTER READY FOR TESTING!")
            print("🌟" * 20)
