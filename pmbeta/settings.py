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

# Sanitize Mapbox style IDs so invalid versions (e.g., light-v12) don't cause 404s
# Returns a known-good style. Allowed: streets-v12, dark-v11, light-v11, outdoors-v12, satellite-streets-v12
# Maps common invalids: light-v12 -> light-v11, streets-v13 -> streets-v12

def sanitize_mapbox_style(user_style: str) -> str:
    default = 'mapbox://styles/mapbox/streets-v12'
    try:
        s = (user_style or '').strip()
        if not s or not s.startswith('mapbox://'):
            return default
        allowed = {
            'mapbox://styles/mapbox/streets-v12',
            'mapbox://styles/mapbox/dark-v11',
            'mapbox://styles/mapbox/light-v11',
            'mapbox://styles/mapbox/outdoors-v12',
            'mapbox://styles/mapbox/satellite-streets-v12',
        }
        if s in allowed:
            return s
        if 'light-v12' in s:
            return 'mapbox://styles/mapbox/light-v11'
        if 'streets-v13' in s:
            return 'mapbox://styles/mapbox/streets-v12'
        return default
    except Exception:
        return default

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

# Helper: sanitize an optional REDIS_URL, ignore common placeholders
from urllib.parse import urlparse

def _valid_redis_url(raw: str | None) -> str | None:
    try:
        if not raw:
            return None
        s = raw.strip()
        # Ignore placeholder patterns from example envs
        if 'user:password@host:port' in s or s.endswith('@host:port') or s.endswith(':port'):
            return None
        u = urlparse(s)
        # Must be redis or rediss scheme
        if u.scheme not in ('redis', 'rediss'):
            return None
        # Ensure netloc and numeric port if present
        # Accessing u.port will raise ValueError if not numeric; treat as invalid
        _ = u.port  # may be None if not provided, which is ok
        return s
    except Exception:
        return None

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
'MOVEMENT_RANGE': 500,  # PK feel: exploration radius
    'MOVEMENT_RANGE_M': 500,  # canonical key
    'INTERACTION_RANGE_M': 30,  # PK-style close interaction range
    'CHUNK_GRANULARITY': 100,  # 0.01 degree chunks like P2K
    'DEFAULT_START_LAT': 41.0646633,  # Cleveland area
    'DEFAULT_START_LON': -80.6391736,
    'ZOOM_LEVEL': 16,  # Maximum zoom level
    'MAPBOX_ACCESS_TOKEN': os.environ.get('MAPBOX_ACCESS_TOKEN', 'pk.eyJ1IjoiamFsbGk5NiIsImEiOiJjbWU3eW9tZnUwOWJuMnJvcmJrN252OGloIn0.0OSOw3J1cDB45AIRS_mEbA'),  # Mapbox access token (env takes precedence)
    'MAPBOX_STYLE': sanitize_mapbox_style(os.environ.get('MAPBOX_STYLE', 'mapbox://styles/mapbox/streets-v12')),  # Map style (override via env, sanitized)

    # PK flag defaults used by services.flags
'FLAG_INFLUENCE_RADIUS_M': int(os.environ.get('FLAG_INFLUENCE_RADIUS_M', '100')),
    'CLAIM_INFLUENCE_RADIUS_M': int(os.environ.get('CLAIM_INFLUENCE_RADIUS_M', '100')),
    'FLAG_CAPTURE_WINDOW_S': int(os.environ.get('FLAG_CAPTURE_WINDOW_S', '180')),
    'CLAIM_CAPTURE_WINDOW_S': int(os.environ.get('CLAIM_CAPTURE_WINDOW_S', '180')),
    'FLAG_PROTECTION_S': int(os.environ.get('FLAG_PROTECTION_S', '360')),
    'CLAIM_PROTECTION_S': int(os.environ.get('CLAIM_PROTECTION_S', '360')),

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
'HEX_SIZE_M': 150,  # PK: smaller, denser hex lattice
    # PK territory radius (also set claim-style keys for services)
    'FLAG_RADIUS_M': 300,
    'CLAIM_RADIUS_M': 300,
    'CLAIM_RADIUS_PER_LEVEL_M': 100,
    # Placement rules (PK style)
    'FLAG_PLACEMENT_MIN_DISTANCE': 200,
    'CLAIM_PLACEMENT_MIN_DISTANCE': 200,
    'CLAIM_PLACEMENT_COST': 50,

    # Persistent NPC density inside flags (PK-style)
    'MIN_FLAG_NPCS': int(os.environ.get('MIN_FLAG_NPCS', '10')),

    # Wild spawn settings outside flags (PK-style wandering mobs)
    'WILD_MIN_NPCS': int(os.environ.get('WILD_MIN_NPCS', '5')),
    'WILD_SPAWN_RADIUS_M': int(os.environ.get('WILD_SPAWN_RADIUS_M', '120')),
}

# Parallel Kingdom-style overrides used by services when present
# These settings are preferred by services over GAME_SETTINGS to create a "PK feel".
PK_SETTINGS = {
    # Movement and interaction
    'MOVEMENT_RANGE_M': int(os.environ.get('PK_MOVEMENT_RANGE_M', '800')),  # keep tests stable at 800
    'INTERACTION_RANGE_M': int(os.environ.get('PK_INTERACTION_RANGE_M', '30')),

    # Territory hex lattice and claim radius
    'HEX_SIZE_M': int(os.environ.get('PK_HEX_SIZE_M', '150')),  # smaller, denser lattice
    'CLAIM_RADIUS_M': int(os.environ.get('PK_CLAIM_RADIUS_M', '300')),
    'CLAIM_RADIUS_PER_LEVEL_M': int(os.environ.get('PK_CLAIM_RADIUS_PER_LEVEL_M', '100')),

    # Placement rules and costs
    'CLAIM_PLACEMENT_MIN_DISTANCE': int(os.environ.get('PK_CLAIM_PLACEMENT_MIN_DISTANCE', '200')),
    'CLAIM_PLACEMENT_COST': int(os.environ.get('PK_CLAIM_PLACEMENT_COST', '50')),

    # Combat/capture windows around territory
    'CLAIM_CAPTURE_WINDOW_S': int(os.environ.get('PK_CLAIM_CAPTURE_WINDOW_S', '180')),
    'CLAIM_PROTECTION_S': int(os.environ.get('PK_CLAIM_PROTECTION_S', '360')),
    'CLAIM_INFLUENCE_RADIUS_M': int(os.environ.get('PK_CLAIM_INFLUENCE_RADIUS_M', '100')),
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
    RAW_REDIS_URL = os.environ.get('REDIS_URL')
    REDIS_URL = _valid_redis_url(RAW_REDIS_URL)
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
        
        # Cache: default to in-memory unless explicitly opted-in
        if os.environ.get('USE_REDIS_CACHE', 'false').lower() == 'true':
            CACHES = {
                'default': {
                    'BACKEND': 'django_redis.cache.RedisCache',
                    'LOCATION': REDIS_URL,
                    'OPTIONS': {
                        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    }
                }
            }
        else:
            CACHES = {
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'pmbeta-default-cache'
                }
            }
        
        # Sessions: default to DB-backed to avoid auth failures if Redis creds are wrong
        if os.environ.get('USE_REDIS_SESSIONS', 'false').lower() == 'true':
            SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
            SESSION_CACHE_ALIAS = 'default'
        else:
            SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    else:
        # Fallback configurations when Redis not available or invalid
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        }
        SESSION_ENGINE = 'django.contrib.sessions.backends.db'
else:
    # Development: prefer Redis if REDIS_URL is valid
    RAW_REDIS_URL = os.environ.get('REDIS_URL')
    REDIS_URL = _valid_redis_url(RAW_REDIS_URL)
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
        # Cache: default to in-memory unless explicitly opted-in
        if os.environ.get('USE_REDIS_CACHE', 'false').lower() == 'true':
            CACHES = {
                'default': {
                    'BACKEND': 'django_redis.cache.RedisCache',
                    'LOCATION': REDIS_URL,
                    'OPTIONS': {
                        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    }
                }
            }
        else:
            CACHES = {
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'pmbeta-default-cache'
                }
            }
        if os.environ.get('USE_REDIS_SESSIONS', 'false').lower() == 'true':
            SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
            SESSION_CACHE_ALIAS = 'default'
        else:
            SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    else:
        # Fallback to in-memory layer when Redis is not configured or invalid
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        }
    # Serve static assets directly from app directories without collectstatic
    # Useful in development where DEBUG may be False
    WHITENOISE_USE_FINDERS = True
