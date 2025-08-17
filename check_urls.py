#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from django.urls import get_resolver
from django.conf import settings

print(f"Current ROOT_URLCONF: {settings.ROOT_URLCONF}")
print(f"Debug mode: {settings.DEBUG}")

resolver = get_resolver()
print("\nAvailable URL patterns:")
for pattern in resolver.url_patterns:
    print(f"- {pattern}")

# Try to reverse the register URL
try:
    from django.urls import reverse
    register_url = reverse('register')
    print(f"\nRegister URL resolves to: {register_url}")
except Exception as e:
    print(f"\nError reversing register URL: {e}")

# Check if the registration app URLs are included
print(f"\nURL patterns details:")
for pattern in resolver.url_patterns:
    print(f"Pattern: {pattern.pattern}")
    if hasattr(pattern, 'url_patterns'):
        print(f"  Sub-patterns: {len(pattern.url_patterns)}")
        for sub in pattern.url_patterns:
            print(f"    - {sub}")
