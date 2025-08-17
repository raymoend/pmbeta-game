"""
Production settings for PMBeta game deployment
"""
import os
from .settings import *

# Security settings for production
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'pmbeta-dev-key-change-in-production')

# Allowed hosts - will be set by hosting platform
ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1',
    '.railway.app',  # Railway domains
    '.vercel.app',   # Vercel domains
    '.herokuapp.com', # Heroku domains
    '.ondigitalocean.app', # DigitalOcean App Platform
]

# Add your custom domain here when you get one
if os.environ.get('CUSTOM_DOMAIN'):
    ALLOWED_HOSTS.append(os.environ.get('CUSTOM_DOMAIN'))

# Database - Use PostgreSQL in production
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    # Fallback to SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Static files settings for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Security middleware
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # Railway handles this
USE_TZ = True

# CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://your-game-domain.com",  # Replace with your actual domain
]

# WebSocket/Channels configuration for production
if os.environ.get('REDIS_URL'):
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [os.environ.get('REDIS_URL')],
            },
        },
    }
else:
    # Fallback to in-memory for development
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Update Mapbox token from environment variable if available
if os.environ.get('MAPBOX_ACCESS_TOKEN'):
    GAME_SETTINGS['MAPBOX_ACCESS_TOKEN'] = os.environ.get('MAPBOX_ACCESS_TOKEN')

# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
