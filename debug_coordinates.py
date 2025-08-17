#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from main.models import NPC, Flag, Player
from django.contrib.auth.models import User

def debug_coordinates():
    print("=== COORDINATE DEBUGGING ===")
    
    # Check players
    players = Player.objects.all()
    print(f"\nPLAYERS ({len(players)}):")
    for player in players:
        print(f"- {player.user.username}: {player.lat}, {player.lon} (Center: {player.center_lat}, {player.center_lon})")
    
    # Check flags
    flags = Flag.objects.all()
    print(f"\nFLAGS ({len(flags)}):")
    for flag in flags:
        print(f"- {flag.name} by {flag.owner.user.username}: {flag.lat}, {flag.lon}")
    
    # Check NPCs
    npcs = NPC.objects.all()
    print(f"\nNPCs ({len(npcs)}):")
    for npc in npcs:
        flag_name = npc.spawned_on_flag.name if npc.spawned_on_flag else "No Flag"
        print(f"- {npc.name}: {npc.lat}, {npc.lon} (Flag: {flag_name}, Alive: {npc.is_alive})")
    
    # Calculate distances
    if players and flags:
        main_player = players[0]
        print(f"\nDISTANCE CALCULATIONS for {main_player.user.username}:")
        
        for flag in flags:
            distance = main_player.distance_between(main_player.lat, main_player.lon, flag.lat, flag.lon)
            print(f"- To {flag.name}: {distance:.2f}m")
        
        for npc in npcs:
            distance = main_player.distance_between(main_player.lat, main_player.lon, npc.lat, npc.lon)
            print(f"- To {npc.name}: {distance:.2f}m")

if __name__ == '__main__':
    debug_coordinates()
