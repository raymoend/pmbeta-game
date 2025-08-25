# PMBeta Deployment Guide

PMBeta is a sophisticated multiplayer location-based mafia game built with Django, Channels, Redis, and Mapbox. This guide covers deploying the game to various hosting platforms with full WebSocket support.

## Features

- **Real-time Multiplayer**: WebSocket-based player movement, chat, and world updates
- **Location-based Gameplay**: Mapbox integration with GPS-based mechanics  
- **Chunk-based World**: Parallel Kingdom-inspired world loading system
- **Mafia Game Mechanics**: Territories, combat, activities, and family system
- **Advanced UI**: Enhanced click detection for mobile gameplay

## Prerequisites

- Python 3.11+
- Redis (for WebSocket channels)
- PostgreSQL (recommended for production)
- Mapbox account and access token

## Quick Deployment Options

Additionally, for local staging with Docker, use docker-compose.staging.yml which includes Postgres, Redis, the web app (Daphne), and a scheduler service running `manage.py process_flags --loop` every 60 seconds.

Quick start (staging locally):

1. docker compose -f docker-compose.staging.yml build
2. docker compose -f docker-compose.staging.yml up -d
3. Visit http://localhost:8000

### 1. Railway (Recommended)

Railway provides excellent support for Django + WebSocket + Redis deployments.

1. **Connect Repository**:
   ```bash
   # Push your code to GitHub/GitLab
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy on Railway**:
   - Go to [railway.app](https://railway.app)
   - Click "Start a New Project" → "Deploy from GitHub repo"
   - Select your PMBeta repository

3. **Add Services**:
   - Add PostgreSQL database service
   - Add Redis service  

4. **Environment Variables**:
   Set these in Railway dashboard:
   ```
   DJANGO_SETTINGS_MODULE=pmbeta.settings_production
   SECRET_KEY=your-generated-secret-key
   MAPBOX_ACCESS_TOKEN=your-mapbox-token
   ```
   
   Railway automatically sets: `DATABASE_URL`, `REDIS_URL`, `PORT`

5. **Deploy**: Railway will automatically build and deploy using the `railway.json` config.

### 2. Heroku

1. **Install Heroku CLI** and login:
   ```bash
   heroku login
   ```

2. **Create App with Add-ons**:
   ```bash
   heroku create your-pmbeta-game
   heroku addons:create heroku-postgresql:essential-0
   heroku addons:create heroku-redis:premium-0
   ```

3. **Set Environment Variables**:
   ```bash
   heroku config:set DJANGO_SETTINGS_MODULE=pmbeta.settings_production
   heroku config:set SECRET_KEY=your-generated-secret-key
   heroku config:set MAPBOX_ACCESS_TOKEN=your-mapbox-token
   ```

4. **Deploy**:
   ```bash
   git push heroku main
   ```

### 3. DigitalOcean App Platform

1. **Create App** from GitHub repository
2. **Configure Services**:
   - Add PostgreSQL database
   - Add Redis database
3. **Set Environment Variables** in the dashboard
4. **Deploy** using the app platform

## Environment Variables

Copy `.env.example` to understand required variables:

```bash
# Essential Variables
SECRET_KEY=your-super-secret-django-key
DJANGO_SETTINGS_MODULE=pmbeta.settings_production
MAPBOX_ACCESS_TOKEN=your-mapbox-access-token

# Database (auto-provided by hosting platforms)
DATABASE_URL=postgres://user:password@host:port/database
REDIS_URL=redis://user:password@host:port

# Optional
DOMAIN_NAME=yourgame.com
DEBUG=False
```

## Local Development with Production Settings

To test production settings locally:

1. **Install Redis** locally or use Docker:
   ```bash
   docker run -d -p 6379:6379 redis:alpine
   ```

2. **Set Environment Variables**:
   ```bash
   set DJANGO_SETTINGS_MODULE=pmbeta.settings_production
   set SECRET_KEY=your-dev-key
   set REDIS_URL=redis://localhost:6379
   set DEBUG=True
   ```

3. **Run with Daphne** (WebSocket support):
   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   daphne -b 0.0.0.0 -p 8000 pmbeta.asgi:application
   ```

## Testing WebSocket Functionality

After deployment:

1. **Open the Game**: Navigate to `https://your-app.railway.app/game/`
2. **Test Real-time Features**:
   - Player movement should be smooth with WebSocket updates
   - Chat messages should appear instantly
   - Other players' movements should be visible in real-time
3. **Check Browser Console**: No WebSocket connection errors
4. **Test Mobile**: Enhanced click detection should work on touch devices

## WebSocket Architecture

PMBeta uses two WebSocket consumers:

- **GameConsumer**: Basic game functionality
- **P2KGameConsumer**: Advanced Parallel Kingdom-style features

Features include:
- Chunk-based world loading
- Real-time player movement with interpolation
- Live chat system
- World state synchronization
- Combat and activity updates

## Production Optimizations

The production settings include:

- **Redis Channel Layer**: Replaces InMemory for scalable WebSockets
- **WhiteNoise**: Efficient static file serving
- **Security Headers**: XSS protection, HSTS, etc.  
- **Database Connection Pooling**: Optimized PostgreSQL connections
- **Static File Compression**: Gzipped assets
- **Session Caching**: Redis-based session storage

## Monitoring and Debugging

1. **Application Logs**:
   - Railway: Check deployment logs in dashboard
   - Heroku: `heroku logs --tail`

2. **WebSocket Issues**:
   - Ensure Redis is connected
   - Check ASGI application is running (not WSGI)
   - Verify `CHANNEL_LAYERS` configuration

3. **Database Issues**:
   - Run migrations: `python manage.py migrate`
   - Check `DATABASE_URL` format

## Custom Domain Setup

1. **Configure DNS**: Point your domain to the hosting platform
2. **Set Environment Variable**: `DOMAIN_NAME=yourgame.com`  
3. **Enable HTTPS**: Uncomment HTTPS settings in production config
4. **Update CORS**: Configure `CORS_ALLOWED_ORIGINS`

## Scaling Considerations

- **Database**: Use connection pooling, read replicas
- **Redis**: Use Redis clustering for high traffic
- **Static Files**: Consider CDN for global distribution  
- **WebSockets**: Use multiple server instances with Redis clustering

## Support

For deployment issues:
- Check the hosting platform's documentation
- Review Django Channels documentation
- Ensure all environment variables are set correctly
- Test locally with production settings first
