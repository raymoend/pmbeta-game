# Railway URL Debugging Guide

This document outlines the debugging steps implemented to resolve the Django `NoReverseMatch` errors occurring in Railway production deployment.

## Issue Summary

The application works perfectly locally but fails in Railway production with:
```
NoReverseMatch at /
Reverse for 'register' not found. 'register' is not a valid view function or pattern name.
```

## Debugging Tools Implemented

### 1. Local URL Configuration Check (`check_urls.py`)
A standalone script that verifies URL configuration in the local environment:
```bash
python check_urls.py
```

### 2. Production URL Debug Script (`debug_railway_urls.py`)
A specialized script for Railway production debugging:
```bash
python debug_railway_urls.py
```

### 3. Live Debug Endpoint (`/debug/urls/`)
A JSON API endpoint accessible at `https://yourdomain.railway.app/debug/urls/` that returns:
- Current Django settings module
- ROOT_URLCONF setting
- Debug mode status
- Railway environment variables
- URL reverse test results
- Available URL patterns

## Changes Made

### Production Settings (`pmbeta/settings_production.py`)
1. **Added explicit ROOT_URLCONF**: Ensures correct URL configuration is loaded
2. **Updated CORS settings**: Added Railway-specific CORS configuration
3. **Railway environment detection**: Special handling for Railway deployment

### Views (`main/views_rpg.py`)
- Added `debug_urls()` view function for live debugging

### URLs (`main/urls_rpg.py`)
- Added `debug/urls/` endpoint route

## How to Use in Railway

1. **Access the debug endpoint**:
   Visit: `https://[your-app].railway.app/debug/urls/`

2. **Check the JSON response** for:
   - `url_tests`: Shows which URLs resolve correctly
   - `url_patterns`: Lists all available URL patterns
   - Environment variables and settings

3. **Compare with local results**:
   Run `python check_urls.py` locally and compare outputs

## Common Issues & Solutions

### Issue: Wrong Django Settings Module
**Symptom**: `django_settings_module` shows unexpected value
**Solution**: Verify Railway environment variable `DJANGO_SETTINGS_MODULE`

### Issue: Missing URL Patterns
**Symptom**: `url_patterns` array is empty or missing expected patterns
**Solution**: Check that `ROOT_URLCONF` points to correct URLs file

### Issue: Import Errors
**Symptom**: URLs fail to load due to Python import errors
**Solution**: Check Railway build logs for import failures

### Issue: CORS Problems
**Symptom**: Frontend cannot access debug endpoint
**Solution**: Verify CORS settings allow Railway domain

## Environment Variables to Check

Ensure these are set in Railway:
- `DJANGO_SETTINGS_MODULE=pmbeta.settings_production`
- `SECRET_KEY=[your-secret-key]`
- `DATABASE_URL=[auto-generated]`
- `RAILWAY_ENVIRONMENT=production`

## Files Modified

- `pmbeta/settings_production.py` - Production settings fixes
- `main/views_rpg.py` - Added debug view
- `main/urls_rpg.py` - Added debug URL
- `check_urls.py` - Local debugging script
- `debug_railway_urls.py` - Production debugging script

## Next Steps

1. Deploy to Railway and access debug endpoint
2. Compare results with local environment
3. Identify specific Railway configuration issues
4. Apply targeted fixes based on debug output

The debug endpoint should remain temporarily until the URL issues are resolved, then can be removed from production for security.
