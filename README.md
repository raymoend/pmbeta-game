# PMBeta - Location-Based Web Game

A real-world location-based multiplayer game inspired by Parallel Kingdom, built with Django and WebSockets.

## Features

- **Real-World Map**: Play on actual geographic locations using Mapbox
- **Real-Time Multiplayer**: Live WebSocket-based player interactions
- **Chunk-Based World**: World divided into geographic chunks for efficient data loading
- **Resource Gathering**: Trees, rocks, and other harvestable resources
- **Building System**: Construct structures at real locations
- **Social Gameplay**: Chat and interact with nearby players

## Technology Stack

- **Backend**: Django 4.2 with Django Channels for WebSockets
- **Database**: SQLite (development) / PostgreSQL (production)
- **Real-time**: Redis for WebSocket message broadcasting
- **Frontend**: HTML5, CSS3, JavaScript with Mapbox GL JS
- **Authentication**: Django's built-in user system

## Installation & Setup

### Prerequisites

- Python 3.8+
- Redis server
- Mapbox access token

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd pmbeta-web

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Redis Setup

**Windows:**
- Download and install Redis from https://github.com/microsoftarchive/redis/releases
- Or use Docker: `docker run -d -p 6379:6379 redis:alpine`

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS with Homebrew
brew install redis

# Start Redis
redis-server
```

### 3. Django Configuration

```bash
# Run database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Collect static files (if needed)
python manage.py collectstatic --noinput
```

### 4. Mapbox Setup

1. Get a Mapbox access token from [Mapbox Account](https://account.mapbox.com/)
2. Create a free account and navigate to your account page
3. Copy your default public token or create a new one
4. Update `pmbeta/settings.py`:

```python
GAME_SETTINGS = {
    # ... other settings ...
    'MAPBOX_ACCESS_TOKEN': 'pk.eyJ1IjoieW91ci11c2VybmFtZSIsImEiOiJjbGR...', # Your Mapbox token
}
```

### 5. Running the Application

You need to run both the Django development server and the Channels worker:

**Terminal 1 - Django Web Server:**
```bash
python manage.py runserver
```

**Terminal 2 - Channels Worker (for WebSockets):**
```bash
python manage.py runworker
```

Background workers (Celery) for periodic game systems
- Celery Worker (processes tasks like NPC density and income):
```bash
celery -A pmbeta worker -l info
```
- Celery Beat (schedules periodic tasks):
```bash
celery -A pmbeta beat -l info
```

The application will be available at: http://localhost:8000

## Game Mechanics

### World Structure
- World divided into 0.01-degree chunks (roughly 1km²)
- Each chunk can contain structures, resources, and players
- Real-time updates when players enter/leave chunks

### Player Movement
- Players can move within an 800-meter radius of their center point
- Movement validated server-side to prevent cheating
- Real-time position updates via WebSockets

### Resources & Structures
- Trees and rocks spawn naturally in the world
- Players can harvest resources by clicking
- Build structures using gathered materials
- All actions tied to real GPS coordinates

## API Endpoints

### REST APIs
- `GET /api/world/` - Get current world data for player
- `POST /api/move/` - Move player (fallback for WebSocket)
- `GET /api/stats/` - Public game statistics
- `POST /api/spawn-structures/` - Admin: Spawn test structures

### WebSocket Endpoint
- `ws://localhost:8000/ws/game/` - Real-time game communication (in-memory by default)
- For production or multi-instance, set REDIS_URL and switch Channels to Redis (see settings.py production block).

#### WebSocket Actions (selected)
- Jump to Flag
  - Request:
    - `{ "type": "jump_to_flag", "flag_id": "<uuid>" }`
  - Response:
    - `{ "type": "jump_to_flag", "result": { "success": true, "location": { "lat": <float>, "lon": <float> } } }`
    - On cooldown: `{ "type": "jump_to_flag", "result": { "success": false, "error": "cooldown", "seconds_remaining": <int> } }`
- Collect Flag Revenue
  - Request:
    - `{ "type": "collect_flag_revenue", "flag_id": "<uuid>" }`
  - Response:
    - `{ "type": "collect_flag_revenue", "result": { "success": true, "collected": <int>, "new_gold": <int> } }`
  - Server also emits a HUD refresh:
    - `{ "type": "character_update", "data": { "gold": <int>, "stamina": <int>, ... } }`

## Development

### Windows quickstart (with Redis and background flag income)

- Open PowerShell in the repo root:
  - scripts\dev_up.ps1
- This will:
  - Start Redis via Docker (if available) or instruct you to start Memurai/Redis
  - Create/activate a venv, install dependencies, run migrations
  - Start the background flag ticker (process_flags --loop) minimized
  - Launch Django on http://localhost:8000

Stop all background processes and Redis (if dockerized):
- scripts\dev_down.ps1

Note: If you don’t want the ticker, run: scripts\dev_up.ps1 -NoTick

### Development

### Project Structure
```
pmbeta-web/
├── main/                 # Main Django app
│   ├── models.py        # Game data models
│   ├── views.py         # Web views and API endpoints
│   ├── consumers.py     # WebSocket consumers
│   ├── routing.py       # WebSocket routing
│   └── templates/       # HTML templates
├── pmbeta/              # Django project settings
│   ├── settings.py      # Configuration
│   ├── urls.py          # URL routing
│   └── asgi.py          # ASGI configuration
└── requirements.txt     # Python dependencies
```

### Key Models
- **Player**: User game data (position, stats, inventory)
- **Chunk**: Geographic world chunks
- **Structure**: Buildings and harvestable objects
- **GameEvent**: Player actions and history

### Adding Features
1. Define new models in `main/models.py`
2. Create database migrations: `python manage.py makemigrations`
3. Add WebSocket handlers in `main/consumers.py`
4. Update frontend JavaScript in game template
5. Add API endpoints in `main/views.py` if needed

## Deployment

### Environment Variables
Set these in production:
- `SECRET_KEY`: Django secret key
- `DEBUG=False`
- `ALLOWED_HOSTS`: Your domain (and Railway wildcard if using Railway)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string (optional; required for multi-instance WebSockets)
- `DJANGO_SETTINGS_MODULE`: Use `pmbeta.settings_production` for production
- `MAPBOX_ACCESS_TOKEN`: Your Mapbox token (override for production)

### Production on Railway (Recommended)

Follow these steps to deploy on Railway with Daphne + Channels:

1) Prerequisites
- Install Railway CLI: `npm i -g @railway/cli`
- Login: `railway login`

2) Create/link project and add services (from repo root)
```
railway init   # or: railway link
railway add postgresql
# Optional (recommended for scale):
railway add redis
```

3) Configure environment variables
```
railway variables set \
  DJANGO_SETTINGS_MODULE=pmbeta.settings \
  SECRET_KEY=<generated-strong-secret> \
  DEBUG=0 \
  RAILWAY_ENVIRONMENT=production \
  ALLOWED_HOSTS="*.up.railway.app,*.railway.app" \
  CSRF_TRUSTED_ORIGINS="https://*.up.railway.app,https://*.railway.app" \
  MAPBOX_ACCESS_TOKEN=<your_mapbox_token>
```
Railway injects `DATABASE_URL` (and `REDIS_URL` if you added Redis) automatically.

4) Healthcheck
- This repo exposes `GET /health/` which returns `{"status":"ok"}`.
- In Railway, set healthcheck path to `/health/`.

5) Start/Predeploy
- This repo ships with `railway.json` that runs:
  - `python set_django_settings.py && python manage.py migrate && python manage.py collectstatic --noinput && python manage.py setup_railway && daphne -b 0.0.0.0 -p $PORT pmbeta.asgi:application`
- `setup_railway` seeds starter items, monster templates, regions, and creates an admin user (default password `admin123`). Override with: `--admin-password=...` by adjusting the start command if desired.

6) Deploy
```
railway up
railway logs -f
```

7) Verify
- Open `https://YOUR-SERVICE.up.railway.app/`
- Health: `https://YOUR-SERVICE.up.railway.app/health/`
- WebSocket path: `wss://YOUR-SERVICE.up.railway.app/ws/game/`

8) Post-deploy
- Create a superuser (optional if not relying on default): `railway run python manage.py createsuperuser`
- For custom domain, update `ALLOWED_HOSTS` (domain only) and `CSRF_TRUSTED_ORIGINS` (with `https://` scheme).
- For multi-instance WebSockets, add Redis service so `CHANNEL_LAYERS` uses `channels-redis`.

### Docker Compose (Dev)

A quick local stack with Postgres, Redis, web, Celery worker and beat is provided.

- Prerequisites: Docker Desktop
- Start the stack:
```bash
# from repo root
docker-compose up --build
```
- First-time seeding (in another shell):
```bash
docker exec -it pmbeta_web python manage.py setup_dev --username=admin --password=admin123
```
- Open http://localhost:8000
- Stop stack: Ctrl+C, then `docker-compose down`

### Docker Deployment (Alternative)
```dockerfile
# Example Dockerfile (Daphne + ASGI)
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .
ENV DJANGO_SETTINGS_MODULE=pmbeta.settings_production
RUN python manage.py collectstatic --noinput || true
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "pmbeta.asgi:application"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is open source. See LICENSE file for details.

## Troubleshooting

### Common Issues

**WebSocket Connection Failed:**
- Ensure Redis is running: `redis-cli ping`
- Check if Channels worker is running
- Verify WebSocket URL in browser console

**Database Errors:**
- Run migrations: `python manage.py migrate`
- Check database connection settings

**Mapbox Map Not Loading:**
- Verify access token is correct
- Check access token restrictions in Mapbox account
- Ensure token has proper scopes for web usage

**Permission Denied Errors:**
- Make sure user is logged in for game access
- Check login redirect URLs in settings

### Performance Tips

- Use Redis for session storage in production
- Enable database connection pooling
- Configure proper caching headers for static files
- Use CDN for Mapbox API calls if needed
- Monitor WebSocket connection counts

For more help, check the Django and Channels documentation.
