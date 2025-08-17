#!/usr/bin/env python3
"""
Test script for crafting system API endpoints
"""
import os
import django
import json

# Setup Django environment first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

# Now import Django modules
from django.test import Client
from django.contrib.auth.models import User

def test_crafting_api():
    """Test the crafting API endpoints"""
    from main.models import Character, InventoryItem, ItemTemplate, CraftingRecipe
    
    # Create test client
    client = Client()
    
    # Get or create a test user and character
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Log in the user
    client.login(username='testuser', password='testpass123')
    
    # Get or create character
    try:
        character = user.character
        # Level up the character for testing
        if character.level < 10:
            character.level = 10  # High enough to craft most items
            character.recalculate_derived_stats()
            character.save()
    except:
        from main.models import Character
        character = Character.objects.create(
            user=user,
            name='TestCrafter',
            lat=0.0, lon=0.0,
            current_hp=100, max_hp=100,
            current_stamina=100, max_stamina=100,
            experience=0, level=10  # High enough to craft most items
        )
        character.recalculate_derived_stats()
        character.save()
    
    print(f"Testing with character: {character.name} (Level {character.level})")
    
    # Add some basic materials to inventory for testing (match recipe requirements)
    materials = {
        'wood': 10,
        'stone': 10,
        'iron_ore': 10,
        'food': 5
    }
    
    for material_name, quantity in materials.items():
        try:
            material_template = ItemTemplate.objects.get(name=material_name)
        except ItemTemplate.DoesNotExist:
            material_template = ItemTemplate.objects.create(
                name=material_name,
                description=f"Basic {material_name.replace('_', ' ')} material",
                item_type='material',
                base_value=10
            )
        
        # Add to inventory
        inventory_item, created = InventoryItem.objects.get_or_create(
            character=character,
            item_template=material_template,
            defaults={'quantity': quantity}
        )
        if not created:
            inventory_item.quantity = max(inventory_item.quantity, quantity)
            inventory_item.save()
    
    print(f"Added test materials to {character.name}'s inventory")
    
    # Test 1: Get available recipes
    print("\n=== Test 1: Available Recipes ===")
    response = client.get('/api/crafting/recipes/')
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {len(data['recipes'])} available recipes")
        craftable_count = sum(1 for r in data['recipes'] if r['can_craft'])
        print(f"  Craftable recipes: {craftable_count}")
        for recipe in data['recipes']:
            status = "✓" if recipe['can_craft'] else "✗"
            reason = f" ({recipe.get('reason', 'Unknown')})" if not recipe['can_craft'] else ""
            print(f"  {status} {recipe['name']} ({recipe['category']}){reason}")
    else:
        print(f"✗ Failed to get recipes: {response.status_code}")
        print(response.content.decode())
    
    # Test 2: Get recipe details
    print("\n=== Test 2: Recipe Details ===")
    if response.status_code == 200:
        data = response.json()
        if data['recipes']:
            first_recipe = data['recipes'][0]
            recipe_response = client.get(f"/api/crafting/recipe/{first_recipe['id']}/")
            if recipe_response.status_code == 200:
                recipe_data = recipe_response.json()
                print(f"✓ Got details for recipe: {recipe_data['recipe']['name']}")
                print(f"  Materials needed: {len(recipe_data['recipe']['materials'])}")
                for material in recipe_data['recipe']['materials']:
                    print(f"    - {material['name']}: {material['have']}/{material['required']} {'✓' if material['is_sufficient'] else '✗'}")
            else:
                print(f"✗ Failed to get recipe details: {recipe_response.status_code}")
    
    # Test 3: Attempt crafting
    print("\n=== Test 3: Attempt Crafting ===")
    if response.status_code == 200:
        data = response.json()
        # Find a recipe we can craft
        craftable_recipe = None
        for recipe in data['recipes']:
            if recipe['can_craft']:
                craftable_recipe = recipe
                break
        
        if craftable_recipe:
            craft_response = client.post('/api/crafting/start/', 
                data=json.dumps({'recipe_id': craftable_recipe['id']}),
                content_type='application/json'
            )
            if craft_response.status_code == 200:
                craft_data = craft_response.json()
                print(f"✓ Crafting attempt completed: {craft_data['message']}")
                if craft_data['result']['crafted']:
                    print(f"  Items created: {craft_data['result']['items_created']}")
                    print(f"  Experience gained: {craft_data['result']['experience_gained']}")
                else:
                    print(f"  Materials consumed: {craft_data['result']['materials_consumed']}")
            else:
                print(f"✗ Failed to start crafting: {craft_response.status_code}")
                print(craft_response.content.decode())
        else:
            print("✗ No craftable recipes found")
    
    # Test 4: Get crafting history
    print("\n=== Test 4: Crafting History ===")
    history_response = client.get('/api/crafting/history/')
    if history_response.status_code == 200:
        history_data = history_response.json()
        print(f"✓ Found {len(history_data['crafting_history'])} crafting attempts in history")
        for attempt in history_data['crafting_history'][:3]:  # Show first 3
            print(f"  - {attempt['recipe_name']}: {attempt['status']} ({attempt['success_rate_used']}% chance)")
    else:
        print(f"✗ Failed to get crafting history: {history_response.status_code}")
    
    # Test 5: Get crafting stats
    print("\n=== Test 5: Crafting Statistics ===")
    stats_response = client.get('/api/crafting/stats/')
    if stats_response.status_code == 200:
        stats_data = stats_response.json()
        stats = stats_data['stats']
        print(f"✓ Crafting Statistics:")
        print(f"  Total attempts: {stats['total_attempts']}")
        print(f"  Success rate: {stats['overall_success_rate']}%")
        print(f"  Crafting skill level: {stats['crafting_skill_level']}")
        if stats['category_breakdown']:
            print("  Category breakdown:")
            for category, category_stats in stats['category_breakdown'].items():
                print(f"    - {category}: {category_stats['successes']}/{category_stats['attempts']} ({category_stats['success_rate']:.1f}%)")
    else:
        print(f"✗ Failed to get crafting stats: {stats_response.status_code}")
    
    print("\n=== Crafting API Test Complete ===")
    
    # Check how many recipes we have total
    total_recipes = CraftingRecipe.objects.filter(is_active=True).count()
    print(f"Total active recipes in database: {total_recipes}")


if __name__ == '__main__':
    test_crafting_api()
