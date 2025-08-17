#!/bin/bash

# Railway startup script for Django deployment
echo "Starting Railway deployment..."

# Set production environment
export DJANGO_SETTINGS_MODULE=pmbeta.settings_production

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if it doesn't exist (optional)
echo "Setting up admin user..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Admin user created: admin/admin123')
else:
    print('Admin user already exists')
"

# Initialize game data
echo "Initializing game data..."
python manage.py shell -c "
from main.views_rpg import create_starter_items, create_monster_templates, create_basic_regions
try:
    create_starter_items()
    create_monster_templates()  
    create_basic_regions()
    print('Game data initialized successfully')
except Exception as e:
    print(f'Game data initialization: {e}')
"

# Start the server
echo "Starting Django server..."
exec daphne -b 0.0.0.0 -p $PORT pmbeta.asgi:application
