#!/usr/bin/env python3
"""
Setup Building System Script
Initialize the building system with default building types and flag colors
"""
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from django.db import transaction
from main.building_models import BuildingType, FlagColor, BuildingTemplate

def setup_building_system():
    """Initialize building system with default data"""
    
    print("🏗️ Setting up Building System...")
    print("=" * 60)
    
    try:
        with transaction.atomic():
            
            # CREATE FLAG COLORS
            print("→ Creating flag colors...")
            flag_colors = [
                # Basic colors (free)
                {'name': 'red', 'hex_color': '#FF0000', 'display_name': 'Red', 'is_premium': False},
                {'name': 'blue', 'hex_color': '#0000FF', 'display_name': 'Blue', 'is_premium': False},
                {'name': 'green', 'hex_color': '#00FF00', 'display_name': 'Green', 'is_premium': False},
                {'name': 'yellow', 'hex_color': '#FFFF00', 'display_name': 'Yellow', 'is_premium': False},
                {'name': 'purple', 'hex_color': '#8000FF', 'display_name': 'Purple', 'is_premium': False},
                {'name': 'orange', 'hex_color': '#FF8000', 'display_name': 'Orange', 'is_premium': False},
                {'name': 'white', 'hex_color': '#FFFFFF', 'display_name': 'White', 'is_premium': False},
                {'name': 'black', 'hex_color': '#000000', 'display_name': 'Black', 'is_premium': False},
                
                # Premium colors (require level or gold)
                {'name': 'gold', 'hex_color': '#FFD700', 'display_name': 'Gold', 'is_premium': True, 'unlock_level': 10, 'unlock_cost': 5000},
                {'name': 'silver', 'hex_color': '#C0C0C0', 'display_name': 'Silver', 'is_premium': True, 'unlock_level': 5, 'unlock_cost': 2500},
                {'name': 'crimson', 'hex_color': '#DC143C', 'display_name': 'Crimson', 'is_premium': True, 'unlock_level': 15, 'unlock_cost': 7500},
                {'name': 'emerald', 'hex_color': '#50C878', 'display_name': 'Emerald', 'is_premium': True, 'unlock_level': 20, 'unlock_cost': 10000},
                {'name': 'sapphire', 'hex_color': '#0F52BA', 'display_name': 'Sapphire', 'is_premium': True, 'unlock_level': 25, 'unlock_cost': 15000},
                {'name': 'royal_purple', 'hex_color': '#6A0DAD', 'display_name': 'Royal Purple', 'is_premium': True, 'unlock_level': 30, 'unlock_cost': 20000},
            ]
            
            for color_data in flag_colors:
                color, created = FlagColor.objects.get_or_create(
                    name=color_data['name'],
                    defaults=color_data
                )
                if created:
                    print(f"  ✓ Created flag color: {color.display_name}")
                else:
                    print(f"  → Flag color exists: {color.display_name}")
            
            # CREATE BUILDING TYPES
            print("\n→ Creating building types...")
            building_types = [
                # Economic Buildings
                {
                    'name': 'Trading Post',
                    'description': 'A basic trading post that generates steady income from merchant activity.',
                    'category': 'economic',
                    'base_cost_gold': 500,
                    'base_cost_wood': 30,
                    'base_cost_stone': 15,
                    'base_revenue_per_hour': 10,
                    'max_revenue_per_hour': 2500,
                    'max_level': 10,
                    'construction_time_minutes': 30,
                    'icon_name': 'trading_post'
                },
                {
                    'name': 'Market',
                    'description': 'A bustling marketplace that attracts traders and generates substantial revenue.',
                    'category': 'economic',
                    'base_cost_gold': 1500,
                    'base_cost_wood': 75,
                    'base_cost_stone': 50,
                    'base_revenue_per_hour': 25,
                    'max_revenue_per_hour': 2500,
                    'max_level': 8,
                    'construction_time_minutes': 60,
                    'icon_name': 'market'
                },
                {
                    'name': 'Bank',
                    'description': 'A secure bank that generates high revenue through financial services.',
                    'category': 'economic',
                    'base_cost_gold': 3000,
                    'base_cost_wood': 50,
                    'base_cost_stone': 100,
                    'base_revenue_per_hour': 50,
                    'max_revenue_per_hour': 2500,
                    'max_level': 6,
                    'construction_time_minutes': 120,
                    'icon_name': 'bank'
                },
                
                # Military Buildings
                {
                    'name': 'Guard Tower',
                    'description': 'A defensive structure that provides protection and generates income from security services.',
                    'category': 'military',
                    'base_cost_gold': 800,
                    'base_cost_wood': 20,
                    'base_cost_stone': 60,
                    'base_revenue_per_hour': 15,
                    'max_revenue_per_hour': 1500,
                    'max_level': 8,
                    'construction_time_minutes': 45,
                    'icon_name': 'guard_tower'
                },
                {
                    'name': 'Fortress',
                    'description': 'A mighty fortress that commands respect and generates revenue from taxation.',
                    'category': 'military',
                    'base_cost_gold': 5000,
                    'base_cost_wood': 100,
                    'base_cost_stone': 200,
                    'base_revenue_per_hour': 40,
                    'max_revenue_per_hour': 2000,
                    'max_level': 5,
                    'construction_time_minutes': 180,
                    'icon_name': 'fortress'
                },
                
                # Utility Buildings
                {
                    'name': 'Workshop',
                    'description': 'A crafting workshop that generates income from creating and selling goods.',
                    'category': 'utility',
                    'base_cost_gold': 1200,
                    'base_cost_wood': 80,
                    'base_cost_stone': 30,
                    'base_revenue_per_hour': 20,
                    'max_revenue_per_hour': 1800,
                    'max_level': 7,
                    'construction_time_minutes': 75,
                    'icon_name': 'workshop'
                },
                {
                    'name': 'Inn',
                    'description': 'A cozy inn that provides lodging for travelers and generates steady revenue.',
                    'category': 'utility',
                    'base_cost_gold': 1000,
                    'base_cost_wood': 60,
                    'base_cost_stone': 25,
                    'base_revenue_per_hour': 18,
                    'max_revenue_per_hour': 1600,
                    'max_level': 8,
                    'construction_time_minutes': 50,
                    'icon_name': 'inn'
                },
                
                # Decorative Buildings
                {
                    'name': 'Monument',
                    'description': 'A grand monument that attracts visitors and generates modest revenue from tourism.',
                    'category': 'decorative',
                    'base_cost_gold': 2000,
                    'base_cost_wood': 40,
                    'base_cost_stone': 80,
                    'base_revenue_per_hour': 12,
                    'max_revenue_per_hour': 800,
                    'max_level': 5,
                    'construction_time_minutes': 90,
                    'icon_name': 'monument'
                },
            ]
            
            for building_data in building_types:
                building_type, created = BuildingType.objects.get_or_create(
                    name=building_data['name'],
                    defaults=building_data
                )
                if created:
                    print(f"  ✓ Created building type: {building_type.name}")
                    print(f"    Revenue: {building_type.base_revenue_per_hour} → {building_type.max_revenue_per_hour} gold/hour")
                else:
                    print(f"  → Building type exists: {building_type.name}")
            
            # CREATE BUILDING TEMPLATES (Starter buildings)
            print("\n→ Creating building templates...")
            
            # Get building types for templates
            trading_post = BuildingType.objects.get(name='Trading Post')
            guard_tower = BuildingType.objects.get(name='Guard Tower')
            
            templates = [
                {
                    'name': 'Starter Trading Post',
                    'building_type': trading_post,
                    'description': 'A basic trading post perfect for new players to start generating income.',
                    'is_starter': True,
                    'level_required': 1,
                    'cost_gold': 250,  # Cheaper for starters
                    'cost_wood': 15,
                    'cost_stone': 10,
                },
                {
                    'name': 'Basic Guard Tower',
                    'building_type': guard_tower,
                    'description': 'A simple guard tower for early defense and income.',
                    'is_starter': True,
                    'level_required': 3,
                    'cost_gold': 400,
                    'cost_wood': 15,
                    'cost_stone': 25,
                },
            ]
            
            for template_data in templates:
                template, created = BuildingTemplate.objects.get_or_create(
                    name=template_data['name'],
                    defaults=template_data
                )
                if created:
                    print(f"  ✓ Created building template: {template.name}")
                else:
                    print(f"  → Building template exists: {template.name}")
            
            print("\n" + "=" * 60)
            print("🎉 BUILDING SYSTEM SETUP COMPLETE!")
            print("=" * 60)
            print("📊 Summary:")
            print(f"   Flag Colors: {FlagColor.objects.count()} total")
            print(f"   Building Types: {BuildingType.objects.count()} total")
            print(f"   Building Templates: {BuildingTemplate.objects.count()} total")
            
            print("\n🏗️ Building Types Available:")
            for building_type in BuildingType.objects.all():
                print(f"   • {building_type.name} ({building_type.get_category_display()})")
                print(f"     Revenue: {building_type.base_revenue_per_hour} → {building_type.max_revenue_per_hour} gold/hour")
                print(f"     Cost: {building_type.base_cost_gold} gold, {building_type.base_cost_wood} wood, {building_type.base_cost_stone} stone")
            
            print("\n🎨 Flag Colors Available:")
            basic_colors = FlagColor.objects.filter(is_premium=False)
            premium_colors = FlagColor.objects.filter(is_premium=True)
            
            print(f"   Basic Colors ({basic_colors.count()}): " + ", ".join([c.display_name for c in basic_colors]))
            print(f"   Premium Colors ({premium_colors.count()}): " + ", ".join([c.display_name for c in premium_colors]))
            
            print("\n🚀 Ready for players to build and generate revenue!")
            print("   • Players can choose flag colors at signup")
            print("   • Buildings generate up to 2500 gold/hour when maxed")
            print("   • Revenue increases with each upgrade level")
            print("   • Buildings can be attacked in PvP for raiding")
            
    except Exception as e:
        print(f"❌ Error setting up building system: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def show_revenue_progression():
    """Show revenue progression for each building type"""
    print("\n📈 Revenue Progression by Building Type:")
    print("=" * 80)
    
    for building_type in BuildingType.objects.all():
        print(f"\n{building_type.name} ({building_type.get_category_display()}):")
        print("Level | Revenue/Hour | Upgrade Cost (Gold)")
        print("-" * 45)
        
        for level in range(1, building_type.max_level + 1):
            revenue = building_type.get_revenue_at_level(level)
            if level < building_type.max_level:
                upgrade_cost = building_type.get_upgrade_cost(level)
                cost_str = f"{upgrade_cost['gold']:,} gold"
            else:
                cost_str = "MAX LEVEL"
            
            print(f"{level:5d} | {revenue:11,} | {cost_str}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'revenue':
        show_revenue_progression()
    else:
        success = setup_building_system()
        if success:
            print("\n" + "🌟" * 20)
            print("BUILDING SYSTEM READY!")
            print("🌟" * 20)
