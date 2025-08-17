#!/usr/bin/env python
"""
Test script for PK Echoes compatible endpoints using player's actual location
"""
import requests
import json
from bs4 import BeautifulSoup

def test_endpoints_with_player_location():
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    # Login
    login_url = f"{base_url}/login/"
    login_page = session.get(login_url)
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    
    login_data = {
        'username': 'IronRay',
        'password': 'testpassword123',
        'csrfmiddlewaretoken': csrf_token
    }
    
    session.post(login_url, data=login_data)
    print("✓ Logged in as IronRay")
    
    # First get player's current location
    mapdata_url = f"{base_url}/api/mapdata/"
    response = session.get(mapdata_url)
    data = response.json()
    
    if data.get('success'):
        player_pos = data['data']['playerPosition']
        player_lat = player_pos['lat']
        player_lon = player_pos['lon']
        
        print(f"Player location: {player_lat}, {player_lon}")
        
        # Now test with player's actual location and a larger radius
        print("\\n=== Testing with Player's Location ===")
        params = {
            'lat': player_lat,
            'lon': player_lon,
            'radius': 0.01  # ~1km radius
        }
        
        response = session.get(mapdata_url, params=params)
        data = response.json()
        
        if data.get('success'):
            map_data = data['data']
            print(f"\\nMap data around player:")
            print(f"- Territories: {len(map_data.get('territories', []))}")
            print(f"- NPCs: {len(map_data.get('npcs', []))}")
            print(f"- Resources: {len(map_data.get('resources', []))}")
            
            # Show territory details
            for territory in map_data.get('territories', []):
                print(f"  Territory: {territory['name']} by {territory['owner']} (Level {territory['level']}, HP: {territory['hp']}/{territory['maxHp']})")
            
            # Show NPC details  
            for npc in map_data.get('npcs', []):
                print(f"  NPC: {npc['name']} (Level {npc['level']}, HP: {npc['hp']}/{npc['maxHp']}, Territory: {npc['territoryId']})")
            
            # Show resource details
            for resource in map_data.get('resources', []):
                print(f"  Resource: {resource['type']} (Level {resource['level']}, Can harvest: {resource['canHarvest']})")
                
        else:
            print(f"Error: {data.get('error')}")
    else:
        print(f"Failed to get player location: {data.get('error')}")

if __name__ == '__main__':
    test_endpoints_with_player_location()
