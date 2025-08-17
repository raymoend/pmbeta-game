# PMBeta Deployment Checklist ✅

## 1. GitHub Setup
- [ ] Create GitHub repository: `pmbeta-game` (PUBLIC)
- [ ] Connect local repo to GitHub
- [ ] Push code to main branch

**Commands to run after creating GitHub repo:**
```bash
git remote add origin https://github.com/raymoend/pmbeta-game.git
git branch -M main
git push -u origin main
```

## 2. Railway Deployment

### A. Create Railway Project
- [ ] Go to [railway.app](https://railway.app)
- [ ] Sign up with GitHub account
- [ ] Click "Deploy from GitHub repo"
- [ ] Select your `pmbeta-game` repository

### B. Add Database Services
- [ ] Add PostgreSQL service (+ New → PostgreSQL)
- [ ] Add Redis service (+ New → Redis)

### C. Set Environment Variables (in main app service)
- [ ] `SECRET_KEY=x(o-+yetba=f#%&1u)5@qq6rbu8y+o2+b2yqz6k^(-@zz5lq3*`
- [ ] `DJANGO_SETTINGS_MODULE=pmbeta.settings_production`
- [ ] `MAPBOX_ACCESS_TOKEN=pk.eyJ1IjoiamFsbGk5NiIsImEiOiJjbWU3eW9tZnUwOWJuMnJvcmJrN252OGloIn0.0OSOw3J1cDB45AIRS_mEbA`
- [ ] `DEBUG=False`

**Note:** Railway automatically sets `DATABASE_URL`, `REDIS_URL`, and `PORT`

### D. Verify Deployment
- [ ] Watch deployment logs complete successfully
- [ ] Click the generated Railway URL
- [ ] Test game login and WebSocket features

## 3. Testing Checklist

After deployment, verify these work:
- [ ] Game loads at `https://your-app.railway.app/game/`
- [ ] User registration/login works
- [ ] Player can move on the map
- [ ] WebSocket connection established (no 404 errors)
- [ ] Real-time chat works
- [ ] NPCs, flags, and resources visible
- [ ] Mobile click detection works

## Troubleshooting

**If deployment fails:**
1. Check Railway deployment logs
2. Verify all environment variables are set
3. Ensure PostgreSQL and Redis services are running
4. Confirm `railway.json` is using Daphne (not Gunicorn)

**If WebSockets don't work:**
1. Check that `REDIS_URL` is set automatically by Railway
2. Verify `CHANNEL_LAYERS` is using Redis in production settings
3. Ensure Daphne ASGI server is running (not WSGI)

**Common issues:**
- Missing `SECRET_KEY` → App won't start
- Wrong settings module → Import errors
- Missing Redis → WebSocket 404 errors
- Wrong Mapbox token → Map won't load

## Your Generated URLs
- Railway URL: `https://your-app-name.up.railway.app`
- Game URL: `https://your-app-name.up.railway.app/game/`
- Admin: `https://your-app-name.up.railway.app/admin/`
