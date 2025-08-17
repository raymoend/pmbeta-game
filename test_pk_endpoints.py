#!/usr/bin/env python
"""
Test script for PK Echoes compatible endpoints
"""
import requests
import json

def test_pk_echoes_endpoints():
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    # Get CSRF token and login
    login_url = f"{base_url}/login/"
    
    # First, get the login page to extract CSRF token
    login_page = session.get(login_url)
    
    # Extract CSRF token from login page HTML
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    
    # Login with test user credentials
    login_data = {
        'username': 'IronRay',
        'password': 'testpassword123',  # You might need to set this password
        'csrfmiddlewaretoken': csrf_token
    }
    
    login_response = session.post(login_url, data=login_data)
    
    if login_response.status_code == 200 and '/game/' in login_response.url:
        print("✓ Successfully logged in as IronRay")
    else:
        print("✗ Login failed - creating new test user")
        # Try to register a new user
        register_url = f"{base_url}/register/"
        register_page = session.get(register_url)
        soup = BeautifulSoup(register_page.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        
        register_data = {
            'username': 'TestPlayer',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
            'csrfmiddlewaretoken': csrf_token
        }
        
        register_response = session.post(register_url, data=register_data)
        print(f"Registration response: {register_response.status_code}")
    
    # Test the PK Echoes compatible endpoints
    print("\n=== Testing PK Echoes Compatible Endpoints ===")
    
    # 1. Test Map Data endpoint
    print("\n1. Testing /api/mapdata/")
    mapdata_url = f"{base_url}/api/mapdata/"
    params = {
        'lat': 40.7128,
        'lon': -74.0060,
        'radius': 0.01
    }
    
    try:
        response = session.get(mapdata_url, params=params)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Response structure:")
            print(f"- Success: {data.get('success')}")
            if data.get('success'):
                map_data = data.get('data', {})
                print(f"- Territories: {len(map_data.get('territories', []))}")
                print(f"- NPCs: {len(map_data.get('npcs', []))}")
                print(f"- Resources: {len(map_data.get('resources', []))}")
                print(f"- Player Position: {map_data.get('playerPosition')}")
        else:
            print(f"Error response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Test Nearby Players endpoint  
    print("\n2. Testing /api/nearbyplayers/")
    nearby_players_url = f"{base_url}/api/nearbyplayers/"
    
    try:
        response = session.get(nearby_players_url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            players = response.json()
            print(f"Nearby players: {len(players)}")
            for player in players[:3]:  # Show first 3
                print(f"- {player.get('username')} (Level {player.get('level')})")
        else:
            print(f"Error response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 3. Test Territories endpoint
    print("\n3. Testing /api/territories/")
    territories_url = f"{base_url}/api/territories/"
    
    try:
        response = session.get(territories_url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Response structure:")
            print(f"- Active Territory: {data.get('activeTerritory', {}).get('name') if data.get('activeTerritory') else 'None'}")
            print(f"- All Territories: {len(data.get('allTerritories', []))}")
            for territory in data.get('allTerritories', [])[:3]:  # Show first 3
                print(f"  - {territory.get('name')} (Level {territory.get('level')}, {territory.get('npcCount')} NPCs)")
        else:
            print(f"Error response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == '__main__':
    try:
        test_pk_echoes_endpoints()
    except ImportError:
        print("This script requires beautifulsoup4 and requests libraries.")
        print("Install with: pip install beautifulsoup4 requests")
    except Exception as e:
        print(f"Test failed: {e}")
