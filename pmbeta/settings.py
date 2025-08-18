"""
Django settings for PMBeta project.
Location-based web game similar to Parallel Kingdom.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'pmbeta-dev-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
# Allow Railway domains and custom domain
ALLOWED_HOSTS = [
    'web-production-2d762.up.railway.app',
    '.railway.app',
    'healthcheck.railway.app',
    'localhost',
    '127.0.0.1',
    'testserver'  # For Django testing
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'corsheaders',
    'main',  # Our main game app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pmbeta.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Remove global templates directory to prioritize app templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pmbeta.wsgi.application'
ASGI_APPLICATION = 'pmbeta.asgi.application'

# Database
if 'DATABASE_URL' in os.environ and os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.parse(
            os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# WebSocket/Channels configuration - disabled for debugging
# if 'REDIS_URL' in os.environ:
#     CHANNEL_LAYERS = {
#         'default': {
#             'BACKEND': 'channels_redis.core.RedisChannelLayer',
#             'CONFIG': {
#                 'hosts': [os.environ.get('REDIS_URL')],
#             },
#         },
#     }
# else:
#     CHANNEL_LAYERS = {
#         'default': {
#             'BACKEND': 'channels.layers.InMemoryChannelLayer',
#         },
#     }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'main' / 'static',
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# CSRF settings for Railway deployment
CSRF_TRUSTED_ORIGINS = [
    'https://web-production-2d762.up.railway.app',
    'https://*.railway.app',
]

# Additional CSRF settings for Railway
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG

# Game-specific settings
GAME_SETTINGS = {
    'MOVEMENT_RANGE': 800,  # meters - how far players can move from their center
    'CHUNK_GRANULARITY': 100,  # 0.01 degree chunks like P2K
    'DEFAULT_START_LAT': 41.0646633,  # Cleveland area
    'DEFAULT_START_LON': -80.6391736,
    'ZOOM_LEVEL': 15,  # Maximum zoom level
    'MAPBOX_ACCESS_TOKEN': 'pk.eyJ1IjoiamFsbGk5NiIsImEiOiJjbWU3eW9tZnUwOWJuMnJvcmJrN252OGloIn0.0OSOw3J1cDB45AIRS_mEbA',  # Your Mapbox access token
    'MAPBOX_STYLE': 'mapbox://styles/mapbox/dark-v11',  # Dark theme for mafia aesthetic
    
    # Mafia-specific settings
    'TERRITORY_INCOME_INTERVAL': 3600,  # Territory income every hour (seconds)
    'HEAT_DECAY_RATE': 0.1,  # Heat points lost per hour
    'MAX_HEAT_LEVEL': 100.0,  # Maximum heat level
    'JAIL_TIME_PER_HEAT': 10,  # Minutes in jail per heat point when arrested
    'HOSPITAL_BASE_TIME': 60,  # Base minutes in hospital after combat loss
    'FAMILY_MAX_SIZE': 50,  # Maximum family members
    'TERRITORY_CONTROL_THRESHOLD': 51.0,  # Influence % needed to control territory
    'COMBAT_RANGE': 100,  # meters - range for attacking other players
    'ACTIVITY_SUCCESS_BONUS': 0.1,  # Bonus success chance per level
    'REPUTATION_DECAY_RATE': 1,  # Reputation points lost per day of inactivity
    
    # Flag territory system (Parallel Kingdom style)
    'FLAG_BASE_RADIUS_METERS': 200,  # Level 1 flag territory radius
    'FLAG_LEVEL_RADIUS_MULTIPLIER': 1.5,  # Multiplier per level (L1:200m, L2:300m, L3:450m, etc)
    'FLAG_PLACEMENT_MIN_DISTANCE': 400,  # Minimum distance between flags (2x base radius)
}

# Authentication settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/game/'
LOGOUT_REDIRECT_URL = '/'

# Railway Production Optimizations
if os.environ.get('RAILWAY_ENVIRONMENT') == 'production':
    # Force DEBUG to False in production
    DEBUG = False
    
    # Enhanced security for production
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Static files optimizations
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    WHITENOISE_USE_FINDERS = True
    
    # Redis configuration for WebSocket channels (if available)
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
        
        # Use Redis for caching if available
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': REDIS_URL,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                }
            }
        }
        
        # Use Redis sessions
        SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
        SESSION_CACHE_ALIAS = 'default'
    else:
        # Fallback configurations when Redis not available
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        }
        SESSION_ENGINE = 'django.contrib.sessions.backends.db'
else:
    # Development: Enable channels for WebSocket functionality
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
