"""
Django settings for PMBeta project.
Location-based web game similar to Parallel Kingdom.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
# Make Celery optional so tests can run without it installed
try:
    from celery.schedules import crontab as _celery_crontab
    def crontab(*args, **kwargs):
        return _celery_crontab(*args, **kwargs)
    _CELERY_AVAILABLE = True
except Exception:
    def crontab(*args, **kwargs):  # type: ignore
        return None
    _CELERY_AVAILABLE = False

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
    '.up.railway.app',
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
# Avoid duplicate collection: app 'main' already provides its static directory via AppDirectoriesFinder.
# Do not add main/static again here, or collectstatic will see duplicates and ignore later copies.
STATICFILES_DIRS = []

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# CSRF settings for Railway deployment
CSRF_TRUSTED_ORIGINS = [
    'https://web-production-2d762.up.railway.app',
    'https://*.up.railway.app',
    'https://*.railway.app',
]

# CSRF cookie settings
# Allow JS to read the CSRF token in development so fetch() can send the header.
# In production, consider reverting HTTPONLY for stricter security if you render tokens into templates instead.
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = not DEBUG

# Celery configuration (optional)
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_TIMEZONE = TIME_ZONE
if _CELERY_AVAILABLE:
    CELERY_BEAT_SCHEDULE = {
        'accrue-flag-income': {
            'task': 'main.tasks.accrue_flag_income',
            'schedule': crontab(minute='*/1'),
        },
        'deduct-flag-upkeep': {
            'task': 'main.tasks.deduct_flag_upkeep',
            'schedule': crontab(minute=15, hour='0'),
        },
        # Maintain persistent NPCs inside territory flags every 2 minutes
        'npc-pulse': {
            'task': 'main.tasks.npc_pulse_task',
            'schedule': crontab(minute='*/2'),
        },
    }
else:
    CELERY_BEAT_SCHEDULE = {}

# Game-specific settings
GAME_SETTINGS = {
    'MOVEMENT_RANGE': 800,  # meters - how far players can move from their center
    'MOVEMENT_RANGE_M': 800,  # meters - canonical key for enforcement
    'INTERACTION_RANGE_M': 50,  # meters - range for harvesting/combat interactions
    'CHUNK_GRANULARITY': 100,  # 0.01 degree chunks like P2K
    'DEFAULT_START_LAT': 41.0646633,  # Cleveland area
    'DEFAULT_START_LON': -80.6391736,
    'ZOOM_LEVEL': 16,  # Maximum zoom level
    'MAPBOX_ACCESS_TOKEN': os.environ.get('MAPBOX_ACCESS_TOKEN', 'pk.eyJ1IjoiamFsbGk5NiIsImEiOiJjbWU3eW9tZnUwOWJuMnJvcmJrN252OGloIn0.0OSOw3J1cDB45AIRS_mEbA'),  # Mapbox access token (env takes precedence)
    'MAPBOX_STYLE': os.environ.get('MAPBOX_STYLE', 'mapbox://styles/mapbox/light-v12'),  # Map style (override via env)

    # PK flag defaults used by services.flags
    'FLAG_INFLUENCE_RADIUS_M': int(os.environ.get('FLAG_INFLUENCE_RADIUS_M', '150')),
    'FLAG_CAPTURE_WINDOW_S': int(os.environ.get('FLAG_CAPTURE_WINDOW_S', '300')),
    'FLAG_PROTECTION_S': int(os.environ.get('FLAG_PROTECTION_S', '600')),

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
    'HEX_SIZE_M': 650,  # Hex grid radius (meters) used for snapping and IDs
    'FLAG_RADIUS_M': 650,  # Circle radius (meters) for server-side presence/adjacency
    'FLAG_BASE_RADIUS_METERS': 200,  # Level 1 flag territory radius (legacy)
    'FLAG_LEVEL_RADIUS_MULTIPLIER': 1.5,  # Multiplier per level (legacy)
    'FLAG_PLACEMENT_MIN_DISTANCE': 400,  # Minimum distance between flags (legacy flow)

    # Persistent NPC density inside flags (PK-style)
    'MIN_FLAG_NPCS': int(os.environ.get('MIN_FLAG_NPCS', '10')),

    # Wild spawn settings outside flags (PK-style wandering mobs)
    'WILD_MIN_NPCS': int(os.environ.get('WILD_MIN_NPCS', '5')),
    'WILD_SPAWN_RADIUS_M': int(os.environ.get('WILD_SPAWN_RADIUS_M', '120')),
}

# Authentication settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/game/'
LOGOUT_REDIRECT_URL = '/login/'

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
        
        # Sessions: default to DB-backed to avoid auth failures if Redis creds are wrong
        if os.environ.get('USE_REDIS_SESSIONS', 'false').lower() == 'true':
            SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
            SESSION_CACHE_ALIAS = 'default'
        else:
            SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    else:
        # Fallback configurations when Redis not available
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        }
        SESSION_ENGINE = 'django.contrib.sessions.backends.db'
else:
    # Development: prefer Redis if REDIS_URL is provided
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
        # Use Redis for caching (sessions optional)
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': REDIS_URL,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                }
            }
        }
        if os.environ.get('USE_REDIS_SESSIONS', 'false').lower() == 'true':
            SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
            SESSION_CACHE_ALIAS = 'default'
        else:
            SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    else:
        # Fallback to in-memory layer when Redis is not configured
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        }
    # Serve static assets directly from app directories without collectstatic
    # Useful in development where DEBUG may be False
    WHITENOISE_USE_FINDERS = True
