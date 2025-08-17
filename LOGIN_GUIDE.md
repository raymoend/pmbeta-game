# PMBeta Login Troubleshooting Guide

## Available Accounts
- **testuser** / **test123** (Fresh superuser)
- **admin** / **admin** (Simple admin)
- **IronRay** / **testpassword123** (Game test user)

## Login URL
http://localhost:8000/login/

## Troubleshooting Steps

### 1. Clear Browser Data
- Clear cookies, cache, and session storage for localhost:8000
- Try incognito/private browsing mode

### 2. Check Server Status
- Make sure Django server is running: `python manage.py runserver 0.0.0.0:8000`
- Visit: http://localhost:8000/debug/login/ to check authentication status

### 3. Try Different Browsers
- Chrome/Edge incognito mode
- Firefox private window
- Different browser entirely

### 4. Manual Login Steps
1. Go to: http://localhost:8000/login/
2. Enter username: `testuser`
3. Enter password: `test123`
4. Click "Sign In"
5. Should redirect to: http://localhost:8000/game/

### 5. Check for JavaScript Errors
- Open browser developer tools (F12)
- Check Console tab for any JavaScript errors
- Check Network tab to see if login POST request is being sent

### 6. Verify CSRF Token
- Right-click on login page → View Page Source
- Look for: `<input type="hidden" name="csrfmiddlewaretoken" value="..."`
- If missing, there's a CSRF issue

### 7. Alternative: Create New Account
1. Go to: http://localhost:8000/register/
2. Create a new account
3. Should auto-login after registration

## Direct URLs After Login
- Game: http://localhost:8000/game/
- Profile: http://localhost:8000/profile/
- Admin (superuser only): http://localhost:8000/admin/

## API Test URLs (require login)
- Player Debug: http://localhost:8000/debug/player/
- Map Data: http://localhost:8000/api/mapdata/
- Territories: http://localhost:8000/api/territories/

If none of these work, the issue might be:
- CSRF middleware configuration
- Session storage issues
- Browser security settings
- Network/firewall blocking cookies
