#!/usr/bin/env python
"""
Debug script for Railway URL issues
This script can be run in production to diagnose URL resolution problems
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings_production')
django.setup()

from django.urls import get_resolver, reverse
from django.conf import settings

print("=== Railway URL Debug Report ===")
print(f"Django Settings Module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
print(f"Current ROOT_URLCONF: {settings.ROOT_URLCONF}")
print(f"Debug mode: {settings.DEBUG}")
print(f"Railway Environment: {os.environ.get('RAILWAY_ENVIRONMENT')}")

# Get URL resolver
resolver = get_resolver()
print(f"\nURL Resolver: {resolver}")

print("\n=== URL Patterns ===")
for i, pattern in enumerate(resolver.url_patterns):
    print(f"{i+1}. {pattern}")
    if hasattr(pattern, 'url_patterns'):
        print(f"   Sub-patterns ({len(pattern.url_patterns)}):")
        for j, sub in enumerate(pattern.url_patterns[:10]):  # Limit to first 10
            print(f"     {j+1}. {sub}")
        if len(pattern.url_patterns) > 10:
            print(f"     ... and {len(pattern.url_patterns) - 10} more")

print("\n=== URL Reverse Tests ===")
urls_to_test = [
    'register',
    'login', 
    'logout',
    'index',
    'rpg_game',
    'character_creation'
]

for url_name in urls_to_test:
    try:
        resolved_url = reverse(url_name)
        print(f"✓ {url_name} -> {resolved_url}")
    except Exception as e:
        print(f"✗ {url_name} -> ERROR: {e}")

print("\n=== Template Context Test ===")
# Test template context like Django would do
from django.template import Context, Template

test_template = Template("Register URL: {% url 'register' %}")
try:
    rendered = test_template.render(Context({}))
    print(f"✓ Template render: {rendered}")
except Exception as e:
    print(f"✗ Template render ERROR: {e}")

print("\n=== Environment Variables ===")
relevant_vars = [
    'DJANGO_SETTINGS_MODULE',
    'RAILWAY_ENVIRONMENT', 
    'PORT',
    'DATABASE_URL',
    'SECRET_KEY'
]

for var in relevant_vars:
    value = os.environ.get(var)
    if value:
        # Mask sensitive values
        if var in ['SECRET_KEY', 'DATABASE_URL']:
            masked_value = value[:10] + '...' if len(value) > 10 else '***'
            print(f"{var}={masked_value}")
        else:
            print(f"{var}={value}")
    else:
        print(f"{var}=Not Set")

print("\n=== End Debug Report ===")
