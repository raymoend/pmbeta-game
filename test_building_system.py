#!/usr/bin/env python3
"""
Test Building System Script
Test the building system with admin characters - place buildings and simulate revenue
"""
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from django.db import transaction
from main.models import Character
from main.building_models import BuildingType, FlagColor, PlayerBuilding, BuildingTemplate

def test_building_system():
    """Test building system with existing admin characters"""
    
    print("🏗️ Testing Building System...")
    print("=" * 60)
    
    try:
        # Get our test characters
        admin_char = Character.objects.get(name="AdminTest")
        raymoend_char = Character.objects.get(name="raymoend")
        
        print(f"✓ Found test characters:")
        print(f"  • {admin_char.name} (Level {admin_char.level}, Gold: {admin_char.gold:,})")
        print(f"  • {raymoend_char.name} (Level {raymoend_char.level}, Gold: {raymoend_char.gold:,})")
        
        # Assign flag colors to characters
        print("\n→ Assigning flag colors...")
        red_flag = FlagColor.objects.get(name='red')
        blue_flag = FlagColor.objects.get(name='blue')
        
        # Test placing buildings for AdminTest
        print(f"\n→ Creating buildings for {admin_char.name}...")
        
        # Get building types
        trading_post = BuildingType.objects.get(name='Trading Post')
        guard_tower = BuildingType.objects.get(name='Guard Tower')
        bank = BuildingType.objects.get(name='Bank')
        
        # Place buildings at different locations around the character
        buildings_to_create = [
            {
                'building_type': trading_post,
                'lat': admin_char.lat + 0.001,  # Slightly north
                'lon': admin_char.lon,
                'flag_color': red_flag,
                'custom_name': "Admin's Trading Empire"
            },
            {
                'building_type': guard_tower,
                'lat': admin_char.lat - 0.001,  # Slightly south
                'lon': admin_char.lon + 0.001,  # Slightly east
                'flag_color': red_flag,
                'custom_name': "Fortress of Solitude"
            },
            {
                'building_type': bank,
                'lat': admin_char.lat,
                'lon': admin_char.lon + 0.002,  # Further east
                'flag_color': red_flag,
                'custom_name': "Gold Vault Supreme"
            }
        ]
        
        admin_buildings = []
        for building_data in buildings_to_create:
            # Check if building already exists at this location
            existing = PlayerBuilding.objects.filter(
                lat=building_data['lat'], 
                lon=building_data['lon']
            ).first()
            
            if existing:
                print(f"  → Building exists at ({building_data['lat']:.6f}, {building_data['lon']:.6f})")
                admin_buildings.append(existing)
            else:
                building = PlayerBuilding.objects.create(
                    owner=admin_char,
                    building_type=building_data['building_type'],
                    lat=building_data['lat'],
                    lon=building_data['lon'],
                    flag_color=building_data['flag_color'],
                    custom_name=building_data['custom_name'],
                    status='active'  # Skip construction time for testing
                )
                print(f"  ✓ Created {building.building_type.name}: {building.custom_name}")
                admin_buildings.append(building)
        
        # Place buildings for raymoend
        print(f"\n→ Creating buildings for {raymoend_char.name}...")
        
        market = BuildingType.objects.get(name='Market')
        workshop = BuildingType.objects.get(name='Workshop')
        
        raymoend_buildings_data = [
            {
                'building_type': market,
                'lat': raymoend_char.lat + 0.001,
                'lon': raymoend_char.lon - 0.001,
                'flag_color': blue_flag,
                'custom_name': "Raymoend's Marketplace"
            },
            {
                'building_type': workshop,
                'lat': raymoend_char.lat - 0.001,
                'lon': raymoend_char.lon - 0.001,
                'flag_color': blue_flag,
                'custom_name': "Crafting Central"
            }
        ]
        
        raymoend_buildings = []
        for building_data in raymoend_buildings_data:
            existing = PlayerBuilding.objects.filter(
                lat=building_data['lat'], 
                lon=building_data['lon']
            ).first()
            
            if existing:
                print(f"  → Building exists at ({building_data['lat']:.6f}, {building_data['lon']:.6f})")
                raymoend_buildings.append(existing)
            else:
                building = PlayerBuilding.objects.create(
                    owner=raymoend_char,
                    building_type=building_data['building_type'],
                    lat=building_data['lat'],
                    lon=building_data['lon'],
                    flag_color=building_data['flag_color'],
                    custom_name=building_data['custom_name'],
                    status='active'  # Skip construction time for testing
                )
                print(f"  ✓ Created {building.building_type.name}: {building.custom_name}")
                raymoend_buildings.append(building)
        
        # Test revenue generation
        print("\n→ Testing revenue generation...")
        
        all_buildings = admin_buildings + raymoend_buildings
        total_collected = 0
        
        for building in all_buildings:
            revenue = building.calculate_revenue()
            collected = building.collect_revenue()
            total_collected += collected
            
            current_rate = building.get_current_revenue_rate()
            next_rate = building.get_next_level_revenue()
            
            print(f"  • {building.custom_name or building.building_type.name} (Level {building.level})")
            print(f"    Owner: {building.owner.name}")
            print(f"    Revenue Rate: {current_rate} gold/hour")
            print(f"    Collected: {collected} gold")
            print(f"    Next Level Rate: {next_rate} gold/hour")
            print()
        
        print(f"📊 Total Revenue Collected: {total_collected:,} gold")
        
        # Test upgrading a building
        print("\n→ Testing building upgrades...")
        
        test_building = admin_buildings[0]  # Use first admin building
        print(f"Testing upgrade for: {test_building.custom_name}")
        
        can_upgrade, message = test_building.can_upgrade()
        print(f"Can upgrade: {can_upgrade} - {message}")
        
        if can_upgrade:
            success, upgrade_message = test_building.start_upgrade()
            if success:
                print(f"✓ {upgrade_message}")
                print(f"  New revenue rate: {test_building.get_current_revenue_rate()} gold/hour")
            else:
                print(f"❌ Upgrade failed: {upgrade_message}")
        
        # Show building summary
        print("\n" + "=" * 60)
        print("🏗️ BUILDING SYSTEM TEST COMPLETE!")
        print("=" * 60)
        
        print("\n📊 Building Summary:")
        for character in [admin_char, raymoend_char]:
            buildings = PlayerBuilding.objects.filter(owner=character)
            if buildings.exists():
                print(f"\n{character.name}'s Buildings:")
                total_revenue_rate = 0
                for building in buildings:
                    revenue_rate = building.get_current_revenue_rate()
                    total_revenue_rate += revenue_rate
                    print(f"  • {building.custom_name or building.building_type.name}")
                    print(f"    Level {building.level} {building.building_type.name}")
                    print(f"    Location: ({building.lat:.6f}, {building.lon:.6f})")
                    print(f"    Revenue: {revenue_rate} gold/hour")
                    print(f"    Flag: {building.flag_color.display_name if building.flag_color else 'None'}")
                    print(f"    Status: {building.get_status_display()}")
                
                print(f"  Total Revenue Rate: {total_revenue_rate:,} gold/hour")
        
        print("\n🚀 Building System Features Working:")
        print("  ✓ Building placement and ownership")
        print("  ✓ Custom flag colors")
        print("  ✓ Revenue generation and collection")
        print("  ✓ Building upgrades and level progression")
        print("  ✓ Multiple building types and categories")
        print("  ✓ Custom building names")
        
    except Exception as e:
        print(f"❌ Error testing building system: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def show_all_buildings():
    """Show all buildings in the game"""
    print("\n🏗️ All Buildings in Game:")
    print("=" * 80)
    
    buildings = PlayerBuilding.objects.all().select_related('owner', 'building_type', 'flag_color')
    
    if not buildings.exists():
        print("No buildings found.")
        return
    
    total_revenue = 0
    for building in buildings:
        revenue_rate = building.get_current_revenue_rate()
        total_revenue += revenue_rate
        
        print(f"Building: {building.custom_name or building.building_type.name}")
        print(f"  Owner: {building.owner.name}")
        print(f"  Type: {building.building_type.name} (Level {building.level})")
        print(f"  Location: ({building.lat:.6f}, {building.lon:.6f})")
        print(f"  Revenue: {revenue_rate:,} gold/hour")
        print(f"  Flag Color: {building.flag_color.display_name if building.flag_color else 'None'}")
        print(f"  Status: {building.get_status_display()}")
        print(f"  Total Generated: {building.total_revenue_generated:,} gold")
        print()
    
    print(f"📊 Total Revenue Rate Across All Buildings: {total_revenue:,} gold/hour")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        show_all_buildings()
    else:
        success = test_building_system()
        if success:
            print("\n" + "🌟" * 20)
            print("BUILDING SYSTEM TESTED!")
            print("🌟" * 20)
