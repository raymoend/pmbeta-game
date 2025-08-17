"""
Django settings for PMBeta project.
Location-based web game similar to Parallel Kingdom.
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'pmbeta-dev-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
# Temporary: Allow all hosts to bypass Railway healthcheck issues
# TODO: Restrict this once Railway deployment is stable
ALLOWED_HOSTS = ['*']

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
        'DIRS': [BASE_DIR / 'templates'],
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
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# WebSocket/Channels configuration
if 'REDIS_URL' in os.environ:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [os.environ.get('REDIS_URL')],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

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
}

# Authentication settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/game/'
LOGOUT_REDIRECT_URL = '/'
