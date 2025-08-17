#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from main.models import NPC

def check_npc_data():
    print("=== NPC DATA AUDIT ===")
    
    # Check database counts
    npcs = NPC.objects.all()
    print(f"Total NPCs in DB: {npcs.count()}")
    print(f"Alive NPCs: {npcs.filter(is_alive=True).count()}")
    print(f"Dead NPCs: {npcs.filter(is_alive=False).count()}")
    
    # Check coordinate validity
    invalid_coords = []
    for npc in npcs:
        if npc.lat < -90 or npc.lat > 90:
            invalid_coords.append(f"{npc.name}: invalid lat {npc.lat}")
        if npc.lon < -180 or npc.lon > 180:
            invalid_coords.append(f"{npc.name}: invalid lon {npc.lon}")
    
    if invalid_coords:
        print(f"INVALID COORDINATES FOUND ({len(invalid_coords)}):")
        for coord in invalid_coords:
            print(f"  - {coord}")
    else:
        print("✓ All coordinates are valid")
    
    # Sample data
    print("\nSample NPC data:")
    for npc in npcs[:5]:
        flag_name = npc.spawned_on_flag.name if npc.spawned_on_flag else "None"
        print(f"  - {npc.id}: {npc.name} at ({npc.lat:.6f}, {npc.lon:.6f}) alive={npc.is_alive} flag={flag_name}")

if __name__ == '__main__':
    check_npc_data()
