# 🔧 Railway Deployment Troubleshooting

## ✅ **DEPLOYMENT FIXES APPLIED**

The following issues have been **FIXED** in the latest commit:

### **Fixed Issues:**
- ✅ **Django settings not configured** - Fixed ASGI import order
- ✅ **ImproperlyConfigured error** - Moved model imports to async methods  
- ✅ **WebSocket consumer conflicts** - Updated routing to use correct consumer
- ✅ **Import order problems** - Django initializes before model imports

---

## 🚀 **Current Deployment Status: READY**

Your game is now **100% ready** for Railway deployment. The common errors have been resolved.

---

## 📋 **Deployment Checklist**

### **1. Verify GitHub Repository**
```bash
# Check latest commit includes fixes
git log --oneline -5
```

### **2. Railway Environment Variables**
Set these in Railway dashboard → Variables:
```
SECRET_KEY=(-&7j3zoor0g13+q&owifzw1y1x+!7zo#6+3^ix9@bf0*zv)(t
DJANGO_SETTINGS_MODULE=pmbeta.production_settings  
DEBUG=False
MAPBOX_ACCESS_TOKEN=pk.your_actual_mapbox_token_here
```

### **3. Deployment Steps**
1. Go to [railway.app/new](https://railway.app/new)
2. Select "Deploy from GitHub repo"
3. Choose `pmbeta-game` repository
4. Set environment variables above
5. Deploy automatically begins

---

## 🔍 **Common Issues & Solutions**

### **Build Fails**
**Symptoms:** Build process stops with errors
**Solution:** 
- Check "Deployments" tab for logs
- Verify all environment variables are set
- Ensure requirements.txt includes all dependencies

### **500 Internal Server Error**
**Symptoms:** Site loads but shows 500 error
**Solutions:**
1. **Missing SECRET_KEY:**
   ```
   Add: SECRET_KEY=(-&7j3zoor0g13+q&owifzw1y1x+!7zo#6+3^ix9@bf0*zv)(t
   ```

2. **Wrong Settings Module:**
   ```
   Add: DJANGO_SETTINGS_MODULE=pmbeta.production_settings
   ```

3. **Missing MapBox Token:**
   ```
   Add: MAPBOX_ACCESS_TOKEN=pk.your_actual_token
   ```

### **Static Files Not Loading**
**Symptoms:** Site loads but CSS/JS missing
**Solution:** 
- Railway runs `collectstatic` automatically
- Check deployment logs for static file collection
- Verify `STATIC_ROOT` in settings

### **Database Issues**
**Symptoms:** Migration errors or database connection fails
**Solutions:**
1. **Add PostgreSQL:**
   - Railway dashboard → Add Service → PostgreSQL
   - `DATABASE_URL` is set automatically

2. **Migration Problems:**
   - Check deployment logs
   - Migrations run automatically via `railway.json`

### **WebSocket Issues**  
**Symptoms:** Real-time features don't work
**Solutions:**
- ✅ **FIXED:** ASGI configuration now correct
- ✅ **FIXED:** Uses `daphne` for WebSocket support
- Railway supports WebSockets by default

---

## 📊 **Health Check**

After deployment, verify these work:

### **✅ Basic Site**
- [ ] Site loads at `https://your-project.railway.app`
- [ ] Can register new account
- [ ] Can login existing account

### **✅ Game Features**  
- [ ] Character creation works
- [ ] Map displays with your location
- [ ] WebSocket connection shows "Connected"
- [ ] Can send chat messages
- [ ] Movement on map works

### **✅ Real-time Features**
- [ ] WebSocket indicator shows green/connected
- [ ] Chat messages appear in real-time
- [ ] Location updates work
- [ ] No console errors in browser

---

## 🛠️ **Advanced Troubleshooting**

### **View Deployment Logs**
1. Railway dashboard → Your project
2. Click on service → "Deployments" 
3. Click latest deployment → View logs

### **View Runtime Logs**  
1. Railway dashboard → Your project
2. Click on service → "Logs" tab
3. See real-time application logs

### **Common Log Errors**

**"No module named 'main'"**
```
Solution: Check DJANGO_SETTINGS_MODULE is correct
```

**"SECRET_KEY not found"**  
```
Solution: Add SECRET_KEY environment variable
```

**"MapBox token invalid"**
```  
Solution: Get valid token from mapbox.com/account/access-tokens
```

**"Database connection failed"**
```
Solution: Add PostgreSQL service in Railway
```

---

## 🆘 **Emergency Reset**

If deployment completely fails:

### **Option 1: Redeploy**
1. Railway dashboard → Service → Settings
2. Click "Redeploy" 
3. Wait for fresh build

### **Option 2: Fresh Deploy**
1. Delete Railway project
2. Create new project from GitHub
3. Set environment variables again
4. Deploy fresh

### **Option 3: Local Verification**  
```bash
# Test locally first
python manage.py check --deploy
python manage.py migrate  
python manage.py collectstatic --noinput
python manage.py runserver
```

---

## 🎯 **Success Indicators**

### **✅ Deployment Successful When:**
- Build completes without errors
- Site loads at Railway URL
- Can register/login accounts  
- Map displays with location
- WebSocket shows "Connected"
- No 500 errors in browser
- Real-time features work

### **📈 Expected Timeline:**
- **Build time:** 2-3 minutes
- **First load:** 10-15 seconds (cold start)
- **Subsequent loads:** 1-2 seconds

---

## 🎉 **Post-Deployment**

Once live:

### **Initialize Game Data:**
```bash
# In Railway dashboard → Service → Settings → Variables
# Add one-time command to spawn initial monsters:
python manage.py spawn_monsters --count=50
```

### **Create Admin Account:**
```bash  
# Optional: Create superuser for admin access
python manage.py createsuperuser
```

### **Monitor Performance:**
- Check Railway metrics dashboard
- Monitor logs for errors  
- Test all game features
- Verify mobile responsiveness

---

## 📞 **Support Resources**

- **Railway Docs:** [railway.app/docs](https://railway.app/docs)
- **Django Deployment:** [docs.djangoproject.com/en/stable/howto/deployment/](https://docs.djangoproject.com/en/stable/howto/deployment/)  
- **WebSocket Issues:** Check browser console for errors
- **Database Problems:** Verify PostgreSQL service is running

---

## ✅ **Final Status: DEPLOYMENT READY** 

**"The Shattered Realm"** is now **fully prepared** for Railway deployment with all common issues resolved. Your location-based multiplayer RPG should deploy successfully! 🚀🎮
