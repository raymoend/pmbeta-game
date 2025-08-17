#!/usr/bin/env python3
"""
Setup verification script for PMBeta
Checks if all dependencies and configuration are correct
"""

import sys
import os
import subprocess

def check_python_version():
    """Check if Python version is adequate"""
    print("1. Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required, got", sys.version)
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n2. Checking Python dependencies...")
    required_packages = [
        'django',
        'channels',
        'channels_redis',
        'redis',
        'corsheaders'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Not installed")
            missing.append(package)
    
    if missing:
        print(f"\nTo install missing packages, run:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    return True

def check_redis():
    """Check if Redis is running"""
    print("\n3. Checking Redis connection...")
    try:
        import redis
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r.ping()
        print("✅ Redis is running and accessible")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("Make sure Redis is installed and running on localhost:6379")
        return False

def check_django_setup():
    """Check Django configuration"""
    print("\n4. Checking Django setup...")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
        import django
        from django.conf import settings
        django.setup()
        
        # Check if settings are loaded
        if hasattr(settings, 'GAME_SETTINGS'):
            print("✅ Django settings loaded")
        else:
            print("❌ Game settings not found")
            return False
            
        # Check database configuration
        from django.core.management import execute_from_command_line
        print("✅ Django management commands available")
        return True
        
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        return False

def check_database():
    """Check database setup"""
    print("\n5. Checking database...")
    try:
        from django.db import connection
        cursor = connection.cursor()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Run: python manage.py migrate")
        return False

def main():
    """Run all checks"""
    print("PMBeta Setup Verification")
    print("=" * 40)
    
    checks = [
        check_python_version,
        check_dependencies,
        check_redis,
        check_django_setup,
        check_database,
    ]
    
    passed = 0
    for check in checks:
        if check():
            passed += 1
        else:
            break  # Stop on first failure
    
    print(f"\n{passed}/{len(checks)} checks passed")
    
    if passed == len(checks):
        print("\n🎉 Setup complete! Ready to run the application:")
        print("1. python manage.py runserver")
        print("2. In another terminal: python -m channels.worker main.consumers")
        print("3. Visit: http://localhost:8000")
    else:
        print(f"\n❌ Setup incomplete. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
