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

def check_npcs():
    print("=== NPC STATUS CHECK ===")
    
    npcs = NPC.objects.all()
    print(f"Total NPCs: {len(npcs)}")
    
    flag_linked = [n for n in npcs if n.spawned_on_flag]
    print(f"Flag-linked NPCs: {len(flag_linked)}")
    
    print("\nNPC Details:")
    for npc in npcs:
        flag_name = npc.spawned_on_flag.name if npc.spawned_on_flag else "None"
        print(f"- {npc.name} (Level {npc.level}, Alive: {npc.is_alive}, Flag: {flag_name})")
    
    print(f"\nFlags: {Flag.objects.count()}")
    for flag in Flag.objects.all():
        linked_npcs = flag.spawned_npcs.count()
        print(f"- {flag.name} ({flag.owner.user.username}) - {linked_npcs} NPCs")
    
    print(f"\nPlayers: {Player.objects.count()}")
    for player in Player.objects.all():
        print(f"- {player.user.username} (${player.cash:,})")

if __name__ == '__main__':
    check_npcs()
