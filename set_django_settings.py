#!/usr/bin/env python3
"""
Simple script to set DJANGO_SETTINGS_MODULE for Railway deployment
This helps ensure we use the correct settings module
"""
import os
import sys

def main():
    # Force the settings module to the main one
    os.environ['DJANGO_SETTINGS_MODULE'] = 'pmbeta.settings'
    
    print(f"DJANGO_SETTINGS_MODULE set to: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print(f"RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', 'Not Set')}")
    print(f"DEBUG: {os.environ.get('DEBUG', 'Not Set')}")
    print(f"SECRET_KEY: {'SET' if os.environ.get('SECRET_KEY') else 'NOT SET'}")
    print(f"DATABASE_URL: {'SET' if os.environ.get('DATABASE_URL') else 'NOT SET'}")

if __name__ == '__main__':
    main()
