# 🚀 Production Deployment Guide

## Overview

This guide covers deploying the Darija Transcription Dashboard to production with security best practices.

## ⚠️ Pre-Deployment Checklist

### 1. **Rotate Compromised Secrets**
- [ ] Generate new GitHub token (current one is exposed)
- [ ] Generate new encryption keys
- [ ] Create strong admin password

### 2. **Environment Setup**
```bash
# Generate secure keys
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

### 3. **Create .env file**
```bash
cp .env.example .env
# Edit .env with your values
```

## 📦 Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Prerequisites
- Docker & Docker Compose installed
- Domain name configured
- SSL certificates (Let's Encrypt recommended)

#### Steps

1. **Clone production branch**
```bash
git clone -b production https://github.com/stntr660/zonemation-darija-dashboard.git
cd zonemation-darija-dashboard
```

2. **Configure environment**
```bash
# Create .env file with production values
cat > .env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
DB_PASSWORD=$(openssl rand -base64 32)
ADMIN_PASSWORD=your-strong-admin-password
ADMIN_EMAIL=admin@yourdomain.com
SENTRY_DSN=your-sentry-dsn-if-using
EOF
```

3. **Build and start services**
```bash
docker-compose up -d --build
```

4. **Check logs**
```bash
docker-compose logs -f app
```

5. **Access application**
- HTTP: http://your-server:8000
- With Nginx: http://your-server

### Option 2: Cloud Platform Deployment

#### Heroku

1. **Install Heroku CLI and login**
```bash
heroku login
```

2. **Create app and add PostgreSQL**
```bash
heroku create zonemation-darija
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini
```

3. **Set environment variables**
```bash
heroku config:set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
heroku config:set ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
heroku config:set FLASK_ENV=production
heroku config:set ADMIN_PASSWORD=your-strong-password
```

4. **Deploy**
```bash
git push heroku production:main
```

5. **Scale dynos**
```bash
heroku ps:scale web=1
```

#### Google Cloud Run

1. **Build container**
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/darija-dashboard
```

2. **Deploy to Cloud Run**
```bash
gcloud run deploy darija-dashboard \
  --image gcr.io/PROJECT-ID/darija-dashboard \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY=$SECRET_KEY,ENCRYPTION_KEY=$ENCRYPTION_KEY
```

#### AWS Elastic Beanstalk

1. **Install EB CLI**
```bash
pip install awsebcli
```

2. **Initialize and create environment**
```bash
eb init -p python-3.11 darija-dashboard
eb create production-env
```

3. **Set environment variables**
```bash
eb setenv SECRET_KEY=$SECRET_KEY ENCRYPTION_KEY=$ENCRYPTION_KEY
```

4. **Deploy**
```bash
eb deploy
```

### Option 3: VPS Deployment (Ubuntu/Debian)

1. **System setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3.11 python3-pip postgresql nginx redis-server ffmpeg -y

# Install supervisor for process management
sudo apt install supervisor -y
```

2. **Database setup**
```bash
# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE darija_db;
CREATE USER darija_user WITH PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE darija_db TO darija_user;
\q
```

3. **Application setup**
```bash
# Clone repository
cd /opt
sudo git clone -b production https://github.com/stntr660/zonemation-darija-dashboard.git
cd zonemation-darija-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements_production.txt

# Set up environment
sudo nano .env  # Add your configuration
```

4. **Configure Supervisor**
```bash
sudo nano /etc/supervisor/conf.d/darija.conf
```

Add:
```ini
[program:darija]
command=/opt/zonemation-darija-dashboard/venv/bin/gunicorn --config gunicorn.conf.py app_production:app
directory=/opt/zonemation-darija-dashboard
user=www-data
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/darija/error.log
stdout_logfile=/var/log/darija/access.log
environment=PATH="/opt/zonemation-darija-dashboard/venv/bin",FLASK_ENV="production"
```

5. **Configure Nginx**
```bash
sudo cp nginx.conf /etc/nginx/sites-available/darija
sudo ln -s /etc/nginx/sites-available/darija /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

6. **Start application**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start darija
```

## 🔒 SSL Certificate Setup

### Using Certbot (Let's Encrypt)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## 📊 Monitoring

### Application Monitoring
- **Sentry**: Set `SENTRY_DSN` in environment
- **New Relic**: Set `NEW_RELIC_LICENSE_KEY` in environment
- **Custom metrics**: Access `/health` endpoint

### Server Monitoring
```bash
# Check application logs
docker-compose logs -f app  # Docker
sudo supervisorctl tail darija  # Supervisor
heroku logs --tail  # Heroku

# Monitor resource usage
htop
docker stats
```

## 🔧 Maintenance

### Database Backup
```bash
# PostgreSQL backup
pg_dump -U darija_user darija_db > backup_$(date +%Y%m%d).sql

# Docker backup
docker-compose exec postgres pg_dump -U darija_user darija_db > backup.sql
```

### Updates
```bash
# Pull latest code
git pull origin production

# Update dependencies
pip install -r requirements_production.txt

# Apply database migrations (if any)
flask db upgrade

# Restart services
docker-compose restart  # Docker
sudo supervisorctl restart darija  # Supervisor
```

## 🚨 Security Considerations

1. **Always use HTTPS in production**
2. **Keep all dependencies updated**
3. **Regularly rotate API keys and tokens**
4. **Monitor logs for suspicious activity**
5. **Implement backup strategy**
6. **Use strong passwords**
7. **Limit database access**
8. **Configure firewall rules**

## 📈 Scaling

### Horizontal Scaling
- Increase Gunicorn workers: Edit `gunicorn.conf.py`
- Add load balancer (Nginx upstream)
- Use Redis for session storage

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Implement caching strategy

## 🆘 Troubleshooting

### Common Issues

1. **Database connection error**
   - Check DATABASE_URL format
   - Verify PostgreSQL is running
   - Check firewall rules

2. **File upload issues**
   - Ensure ffmpeg is installed
   - Check file permissions on uploads directory
   - Verify MAX_CONTENT_LENGTH setting

3. **Rate limiting issues**
   - Check Redis connection
   - Adjust rate limits in config

4. **SSL issues**
   - Verify certificate paths
   - Check Nginx configuration
   - Ensure ports 80/443 are open

## 📞 Support

For deployment issues:
1. Check application logs
2. Review this documentation
3. Open issue on GitHub repository

---

**Remember**: Never commit sensitive data like passwords or API keys to version control!