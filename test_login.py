#!/usr/bin/env python
"""
Test login functionality
"""
import requests
from bs4 import BeautifulSoup

def test_login():
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("=== Login Test ===")
    
    # Step 1: Get login page
    print("1. Getting login page...")
    login_url = f"{base_url}/login/"
    
    try:
        response = session.get(login_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed to get login page: {response.text[:200]}")
            return
            
        # Step 2: Extract CSRF token
        print("2. Extracting CSRF token...")
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_input:
            print("ERROR: No CSRF token found in login page")
            print("Login page HTML snippet:")
            print(response.text[:500])
            return
            
        csrf_token = csrf_input['value']
        print(f"CSRF token: {csrf_token[:20]}...")
        
        # Step 3: Try to login with different user accounts
        test_accounts = [
            ('IronRay', 'testpassword123'),
            ('admin', 'admin123'),  # Common admin password
            ('IRONRAY', 'testpassword123')
        ]
        
        for username, password in test_accounts:
            print(f"\n3. Attempting login with: {username}")
            
            login_data = {
                'username': username,
                'password': password,
                'csrfmiddlewaretoken': csrf_token
            }
            
            login_response = session.post(login_url, data=login_data, allow_redirects=False)
            print(f"Login response status: {login_response.status_code}")
            
            if login_response.status_code == 302:
                redirect_url = login_response.headers.get('Location', '')
                print(f"Redirected to: {redirect_url}")
                
                if '/game/' in redirect_url or redirect_url == '/':
                    print(f"✓ SUCCESS: Login successful for {username}")
                    
                    # Test accessing a protected page
                    game_response = session.get(f"{base_url}/game/")
                    if game_response.status_code == 200 and 'PMBeta' in game_response.text:
                        print("✓ Can access game page")
                    else:
                        print("✗ Cannot access game page after login")
                    
                    return
                else:
                    print(f"✗ Redirected to unexpected location: {redirect_url}")
            elif login_response.status_code == 200:
                # Login failed, stayed on login page
                print("✗ Login failed - stayed on login page")
                soup = BeautifulSoup(login_response.text, 'html.parser')
                error_messages = soup.find_all(class_='errorlist')
                if error_messages:
                    for error in error_messages:
                        print(f"Error: {error.get_text()}")
                else:
                    print("No specific error message found")
            else:
                print(f"✗ Unexpected response: {login_response.status_code}")
        
        print("\n❌ All login attempts failed")
        
    except Exception as e:
        print(f"Error during login test: {e}")

if __name__ == '__main__':
    test_login()
