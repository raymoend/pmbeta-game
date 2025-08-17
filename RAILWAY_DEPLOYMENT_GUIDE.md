# 🚀 Deploy "The Shattered Realm" to Railway

Follow these steps to deploy your RPG game to Railway.app

## 📋 Prerequisites

1. ✅ **GitHub Repository** - Your code is already pushed to GitHub
2. ✅ **Railway Account** - Sign up at [railway.app](https://railway.app)
3. ✅ **MapBox Account** - Get your access token from [mapbox.com](https://mapbox.com)

---

## 🚀 Step-by-Step Deployment

### **Step 1: Create Railway Project**

1. Go to **[railway.app](https://railway.app)**
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your **`pmbeta-game`** repository
5. Railway will automatically detect it's a Django app

### **Step 2: Configure Environment Variables**

Once your project is created, go to your project dashboard:

1. Click on your **service** (should be named after your repo)
2. Go to the **"Variables"** tab
3. Add these **REQUIRED** environment variables:

```bash
SECRET_KEY=(-&7j3zoor0g13+q&owifzw1y1x+!7zo#6+3^ix9@bf0*zv)(t
DJANGO_SETTINGS_MODULE=pmbeta.production_settings
DEBUG=False
MAPBOX_ACCESS_TOKEN=pk.your_actual_mapbox_token_here
```

### **Step 3: Get Your MapBox Token** 

1. Go to **[mapbox.com](https://mapbox.com)**
2. Sign up for a **free account**
3. Go to **Account → Access Tokens**
4. Copy your **Public Token** (starts with `pk.`)
5. Replace `pk.your_actual_mapbox_token_here` with your real token

### **Step 4: Add Database (Optional)**

For production, add PostgreSQL:

1. In Railway dashboard, click **"+ Add Service"**
2. Select **"PostgreSQL"**  
3. Railway will automatically set the `DATABASE_URL` variable

### **Step 5: Deploy!**

1. Railway will **automatically deploy** when you push to GitHub
2. Wait for the build to complete (2-3 minutes)
3. Your game will be live at: `https://your-app-name.railway.app`

---

## ⚡ **Quick Deploy Links**

**Deploy to Railway in 1-click:**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

*Or manually connect your GitHub repository*

---

## 🔧 **Environment Variables Reference**

| Variable | Value | Required |
|----------|--------|----------|
| `SECRET_KEY` | Your Django secret key | ✅ Yes |
| `DJANGO_SETTINGS_MODULE` | `pmbeta.production_settings` | ✅ Yes |
| `DEBUG` | `False` | ✅ Yes |
| `MAPBOX_ACCESS_TOKEN` | Your MapBox public token | ✅ Yes |
| `DATABASE_URL` | Auto-set by Railway PostgreSQL | Optional |
| `REDIS_URL` | Auto-set by Railway Redis | Optional |

---

## 🎮 **Post-Deployment Steps**

### **1. Create Superuser** (Optional)
```bash
# In Railway dashboard → Service → Settings → Deploy
# Add this to a one-time deployment command:
python manage.py createsuperuser
```

### **2. Initialize Game Data**
```bash
# Spawn initial monsters and locations
python manage.py spawn_monsters --count=50
```

### **3. Test Your Game**
1. Visit your Railway URL
2. Register a new account  
3. Create your character
4. Start playing The Shattered Realm!

---

## 🌐 **Custom Domain** (Optional)

To use your own domain:

1. In Railway: **Settings → Domains** 
2. Add your custom domain
3. Update DNS records as instructed
4. Add domain to `ALLOWED_HOSTS` in settings

---

## 🔍 **Troubleshooting**

### **Build Fails?**
- Check the **"Deployments"** tab for error logs
- Most common issue: Missing environment variables

### **500 Error?**
- Check **"Logs"** tab for Python errors
- Verify `SECRET_KEY` and `MAPBOX_ACCESS_TOKEN` are set

### **Static Files Not Loading?**
- Railway automatically handles static files with `collectstatic`
- Check `STATIC_ROOT` and `STATICFILES_DIRS` in settings

### **WebSockets Not Working?**
- Railway supports WebSockets by default
- Check that `daphne` is being used (it is in our config)

---

## 🎉 **You're Live!**

Once deployed, your **"The Shattered Realm"** RPG will be available at:
`https://your-project.railway.app`

**Features that work immediately:**
- ✅ Real-time multiplayer gameplay
- ✅ Location-based gaming with GPS  
- ✅ Interactive MapBox integration
- ✅ Combat system with monsters
- ✅ Quest generation and progression
- ✅ Player chat and trading
- ✅ Character advancement
- ✅ Mobile-responsive design

**Welcome to The Shattered Realm! 🗡️🌍**
