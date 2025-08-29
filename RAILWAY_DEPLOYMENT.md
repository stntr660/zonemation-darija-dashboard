# 🚂 Railway Deployment Guide

## Quick Start ($5/month)

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended for easy deployment)
3. You get $5 free credits to start

### Step 2: Deploy via GitHub

#### Option A: Deploy with One Click (Easiest)
1. Click this button: [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/stntr660/zonemation-darija-dashboard&branch=production)

#### Option B: Deploy from Dashboard
1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose `zonemation-darija-dashboard`
5. Select `production` branch
6. Railway will auto-detect and start deployment

### Step 3: Add PostgreSQL Database
1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway automatically connects it to your app

### Step 4: Add Redis (for rate limiting)
1. Click **"+ New"** again
2. Select **"Database"** → **"Add Redis"**
3. Auto-connected to your app

### Step 5: Configure Environment Variables

Click on your app service, go to **Variables** tab, and add:

```bash
# Required Variables (Generate these!)
SECRET_KEY=<generate with command below>
ENCRYPTION_KEY=<generate with command below>
FLASK_ENV=production

# Admin Setup
ADMIN_USERNAME=admin
ADMIN_EMAIL=your-email@domain.com
ADMIN_PASSWORD=your-secure-password-here

# Database (Railway auto-adds these)
DATABASE_URL=<auto-provided by Railway>
REDIS_URL=<auto-provided by Railway>

# Optional
SENTRY_DSN=<your-sentry-dsn-if-using>
```

**Generate secure keys:**
```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 6: Deploy!
Railway automatically deploys when you:
1. Push to your GitHub repository
2. Update environment variables
3. Make changes in Railway dashboard

## 📱 Access Your App

### Railway Domain
Your app will be available at:
```
https://your-app-name.up.railway.app
```

### Custom Domain (Optional)
1. Go to your service **Settings**
2. Under **Domains**, click **"+ Custom Domain"**
3. Add your domain (e.g., `darija.zonemation.com`)
4. Update your DNS:
   - Type: CNAME
   - Name: darija (or @ for root)
   - Value: your-app-name.up.railway.app

## 🛠️ Railway CLI (Optional)

### Install CLI
```bash
# macOS
brew install railway

# Or with npm
npm install -g @railway/cli
```

### Login
```bash
railway login
```

### Link Project
```bash
cd "/Users/mac/Documents/Zonemation/Transformation digital/Ai darija voice/dashboard"
railway link
```

### Deploy from CLI
```bash
railway up
```

### View Logs
```bash
railway logs
```

### Run Commands
```bash
# Open shell
railway run bash

# Run migrations
railway run python app_production.py db upgrade
```

## 📊 Monitoring

### View Logs
1. Go to your Railway project
2. Click on your service
3. Click **"View Logs"**

### Metrics
Railway provides:
- CPU usage
- Memory usage
- Network usage
- Response times

### Health Checks
Railway automatically checks `/health` endpoint

## 💰 Costs

### Pricing Structure
- **Hobby Plan**: $5/month (includes $5 usage)
- **Pro Plan**: $20/month (includes $20 usage)

### Typical Usage for Your App
- App (1GB RAM): ~$3-5/month
- PostgreSQL: Included
- Redis: Included
- **Total**: Within $5 Hobby plan

### Monitor Usage
Check usage in Railway dashboard → **"Usage"** tab

## 🔧 Troubleshooting

### Build Fails
```bash
# Check logs
railway logs

# Ensure requirements_production.txt is correct
# Ensure Python version matches
```

### Database Connection Issues
```bash
# Railway auto-injects DATABASE_URL
# Format: postgresql://user:pass@host:port/dbname

# Test connection
railway run python -c "from app_production import db; db.create_all()"
```

### Port Issues
Railway uses `PORT` environment variable. Our Gunicorn config handles this automatically.

### FFmpeg Missing
Our `nixpacks.toml` includes ffmpeg. If issues persist:
1. Check build logs
2. Ensure nixpacks.toml is in root directory

## 🚀 First Deployment Checklist

- [ ] Generated SECRET_KEY
- [ ] Generated ENCRYPTION_KEY  
- [ ] Set ADMIN_PASSWORD
- [ ] PostgreSQL provisioned
- [ ] Redis provisioned
- [ ] Environment variables configured
- [ ] Deployment successful
- [ ] Accessed app URL
- [ ] Logged in as admin
- [ ] Changed admin password

## 🔄 Updates

### Auto-deploy from GitHub
```bash
git add .
git commit -m "Update production"
git push origin production
# Railway auto-deploys!
```

### Manual Deploy
```bash
railway up
```

### Rollback
1. Go to Railway dashboard
2. Click **"Deployments"**
3. Find previous deployment
4. Click **"Rollback"**

## 🆘 Support

- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
- Railway Docs: [docs.railway.app](https://docs.railway.app)
- GitHub Issues: Your repository

---

**Ready to deploy? Start with Step 1 above!** 🚀