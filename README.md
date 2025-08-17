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
- `ws://localhost:8000/ws/game/` - Real-time game communication

## Development

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
- `ALLOWED_HOSTS`: Your domain
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

### Docker Deployment
```dockerfile
# Example Dockerfile structure
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
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
