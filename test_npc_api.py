#!/usr/bin/env python
import requests
import json

# Test the NPC API endpoint
def test_npc_api():
    print("=== TESTING NPC API ===")
    
    # You'll need to get a session cookie by logging in first
    session = requests.Session()
    
    # Login first (replace with actual credentials)
    login_url = "http://127.0.0.1:8000/login/"
    login_data = {
        'username': 'IronRay',  # Adjust as needed
        'password': 'your_password',  # You'll need the actual password
    }
    
    try:
        # Get login page first to get CSRF token
        login_page = session.get(login_url)
        csrf_token = None
        
        # Extract CSRF token from the login form
        # For now, let's skip login and test API directly if possible
        
        # Test NPC API endpoint
        api_url = "http://127.0.0.1:8000/api/npcs/"
        response = session.get(api_url)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            if data.get('success'):
                npcs = data.get('data', {}).get('npcs', [])
                print(f"NPCs returned: {len(npcs)}")
                
                # Show sample NPC data
                if npcs:
                    print("Sample NPC:")
                    sample_npc = npcs[0]
                    for key, value in sample_npc.items():
                        print(f"  {key}: {value}")
        else:
            print(f"Error: {response.text}")
            print("Note: You need to be logged in to access this API")
            
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == '__main__':
    test_npc_api()
