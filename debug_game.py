#!/usr/bin/env python3
"""
Debug script to test game loading
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from main.models import Player, Flag
from django.contrib.auth.models import User
from django.conf import settings

def debug_game_status():
    print("=== PMBeta Game Debug ===")
    print()
    
    # Check database connectivity
    try:
        user_count = User.objects.count()
        print(f"✓ Database connected - {user_count} users found")
    except Exception as e:
        print(f"✗ Database error: {e}")
        return
    
    # Check game settings
    print(f"✓ Game settings loaded:")
    print(f"  - Mapbox token: {'Present' if settings.GAME_SETTINGS.get('MAPBOX_ACCESS_TOKEN') else 'Missing'}")
    print(f"  - Default location: {settings.GAME_SETTINGS['DEFAULT_START_LAT']}, {settings.GAME_SETTINGS['DEFAULT_START_LON']}")
    print(f"  - Movement range: {settings.GAME_SETTINGS['MOVEMENT_RANGE']}m")
    
    # Check models
    try:
        player_count = Player.objects.count()
        flag_count = Flag.objects.count()
        print(f"✓ Models working - {player_count} players, {flag_count} flags")
    except Exception as e:
        print(f"✗ Model error: {e}")
    
    # Check if superuser exists
    try:
        superusers = User.objects.filter(is_superuser=True)
        if superusers.exists():
            print(f"✓ Superuser exists: {', '.join([u.username for u in superusers])}")
        else:
            print("⚠ No superuser found - create one with: python manage.py createsuperuser")
    except Exception as e:
        print(f"✗ User check error: {e}")
    
    print()
    print("=== Next Steps ===")
    print("1. Start server: python manage.py runserver")
    print("2. Visit: http://127.0.0.1:8000/")
    print("3. Login with superuser account")
    print("4. Navigate to game: http://127.0.0.1:8000/game/")
    print("5. Press 'F' key to open flag controls")

if __name__ == "__main__":
    debug_game_status()
