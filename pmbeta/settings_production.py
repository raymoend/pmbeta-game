"""
Production settings for PMBeta
Optimized for deployment with Redis, PostgreSQL, and environment variables
"""

import os
import sys
import dj_database_url
from .settings import *

# Override development settings for production
DEBUG = False

# Ensure correct URL configuration is used
ROOT_URLCONF = 'pmbeta.urls'

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_urlsafe(50)
    print(f"WARNING: Using generated SECRET_KEY. Set SECRET_KEY environment variable for production.")

ALLOWED_HOSTS = [
    os.environ.get('DOMAIN_NAME', ''),
    '.onrender.com',  # Render deployment
    '.railway.app',   # Railway deployment
    '.herokuapp.com', # Heroku deployment
    '.vercel.app',    # Vercel deployment
    'localhost',
    '127.0.0.1',
]

# Remove empty strings from ALLOWED_HOSTS
ALLOWED_HOSTS = [host for host in ALLOWED_HOSTS if host]

# Database configuration
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.parse(
            os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback to SQLite for simple deployments
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Redis configuration for WebSocket channels
# Temporarily disabled for Railway deployment debugging
REDIS_URL = os.environ.get('REDIS_URL')

if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [REDIS_URL],
                "capacity": 1500,
                "expiry": 10,
            },
        },
    }
else:
    # Fallback to in-memory channel layer if Redis not available
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS settings (uncomment when using HTTPS)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Static files directories: leave empty; app static is discovered via AppDirectoriesFinder.
# Adding main/static here duplicates entries and causes collectstatic warnings/ignores.
STATICFILES_DIRS = []

# Use WhiteNoise for static file serving
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# WhiteNoise static file compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Additional WhiteNoise settings
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG

# Media files (if using file uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CORS settings for production
if os.environ.get('FRONTEND_URL'):
    CORS_ALLOWED_ORIGINS = [os.environ.get('FRONTEND_URL')]
elif os.environ.get('RAILWAY_ENVIRONMENT'):
    # For Railway deployment, allow all origins temporarily for debugging
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
else:
    # Default production CORS settings
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_ALL_ORIGINS = False

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'daphne': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'daphne.server': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'daphne.access': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'channels': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'asyncio': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Game settings - use environment variables for sensitive data
# Ensure GAME_SETTINGS exists (should inherit from base settings but let's be explicit)
try:
    GAME_SETTINGS
except NameError:
    GAME_SETTINGS = {
        'MOVEMENT_RANGE': 800,
        'CHUNK_GRANULARITY': 100,
        'DEFAULT_START_LAT': 41.0646633,
        'DEFAULT_START_LON': -80.6391736,
        'ZOOM_LEVEL': 15,
        'MAPBOX_ACCESS_TOKEN': 'pk.eyJ1IjoiamFsbGk5NiIsImEiOiJjbWU3eW9tZnUwOWJuMnJvcmJrN252OGloIn0.0OSOw3J1cDB45AIRS_mEbA',
        'MAPBOX_STYLE': 'mapbox://styles/mapbox/dark-v11',
    }

if os.environ.get('MAPBOX_ACCESS_TOKEN'):
    GAME_SETTINGS['MAPBOX_ACCESS_TOKEN'] = os.environ.get('MAPBOX_ACCESS_TOKEN')

# Cache configuration (optional but recommended)
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }

# Session configuration
if REDIS_URL:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Use database sessions if Redis not available
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    
SESSION_COOKIE_AGE = 86400  # 24 hours

# Email configuration (optional - for password reset, etc.)
if os.environ.get('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@pmbeta.com')
