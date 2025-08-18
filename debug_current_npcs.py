#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from main.models import Character, Monster, ResourceNode
from django.contrib.auth.models import User

def debug_current_entities():
    print("=== CURRENT GAME ENTITIES DEBUG ===")
    
    # Check characters (players)
    characters = Character.objects.all()
    print(f"\nCHARACTERS ({len(characters)}):")
    for char in characters:
        print(f"- {char.name} (Level {char.level}): {char.lat}, {char.lon}")
    
    # Check monsters (NPCs)
    monsters = Monster.objects.all()
    print(f"\nMONSTERS/NPCs ({len(monsters)}):")
    for monster in monsters:
        alive_status = "Alive" if monster.is_alive else "Dead"
        print(f"- {monster.template.name} (Level {monster.template.level}, {alive_status}): {monster.lat}, {monster.lon}")
    
    # Check resource nodes
    resources = ResourceNode.objects.all()
    print(f"\nRESOURCE NODES ({len(resources)}):")
    for resource in resources:
        depleted = "Depleted" if resource.is_depleted else f"{resource.quantity}/{resource.max_quantity}"
        print(f"- {resource.get_resource_type_display()} (Level {resource.level}, {depleted}): {resource.lat}, {resource.lon}")
    
    # Calculate distances if we have characters
    if characters and (monsters or resources):
        main_char = characters[0]
        print(f"\nDISTANCE CALCULATIONS for {main_char.name}:")
        
        for monster in monsters:
            distance = main_char.distance_to(monster.lat, monster.lon)
            print(f"- To {monster.template.name}: {distance:.2f}m")
        
        for resource in resources[:5]:  # Show first 5 resources
            distance = main_char.distance_to(resource.lat, resource.lon)
            print(f"- To {resource.get_resource_type_display()}: {distance:.2f}m")
        
        if len(resources) > 5:
            print(f"  ... and {len(resources) - 5} more resources")

if __name__ == '__main__':
    debug_current_entities()
