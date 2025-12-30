# Deployment Guide - Meu Financeiro

Complete guide for deploying and updating the Meu Financeiro application on a VPS.

## Table of Contents

1. [Initial VPS Setup](#initial-vps-setup)
2. [First-Time Deployment](#first-time-deployment)
3. [Updating the Application](#updating-the-application)
4. [Database Management](#database-management)
5. [SSL Certificate Setup](#ssl-certificate-setup)
6. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
7. [Backup and Restore](#backup-and-restore)

---

## Initial VPS Setup

### Prerequisites

- Ubuntu 22.04 LTS or similar Linux distribution
- Root or sudo access
- Domain name pointing to your VPS IP address

### 1. Install Required Software

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose -y

# Install Git
sudo apt install git -y

# Install PostgreSQL client (for backups)
sudo apt install postgresql-client -y

# Reboot or logout/login to apply docker group changes
```

### 2. Configure Firewall

```bash
# Allow SSH, HTTP, and HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. Create Application Directory

```bash
# Create app directory
sudo mkdir -p /opt/meu-financeiro
sudo chown $USER:$USER /opt/meu-financeiro
cd /opt/meu-financeiro
```

---

## First-Time Deployment

### 1. Clone the Repository

```bash
cd /opt/meu-financeiro
git clone https://github.com/YOUR_USERNAME/meu-financeiro.git .
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

Required environment variables:

```bash
# Django Settings
SECRET_KEY=your-long-random-secret-key-here
DEBUG=false
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# CSRF (required for HTTPS)
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Database - PostgreSQL (Supabase or other)
DATABASE_URL=postgresql://user:password@host:port/database

# Gemini AI (optional)
GEMINI_API_KEY=your-api-key-here
```

**Generate SECRET_KEY:**
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 3. Update Nginx Configuration

Edit [nginx/nginx.conf](nginx/nginx.conf) and replace `meu-financeiro.tec.br` with your domain:

```bash
nano nginx/nginx.conf
```

Replace all occurrences of:
- `meu-financeiro.tec.br` → `your-domain.com`

### 4. Setup SSL Certificate (Let's Encrypt)

See [SSL Certificate Setup](#ssl-certificate-setup) section below.

### 5. Build and Start Services

```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Build Docker images
docker compose build

# Run migrations
docker compose run --rm web python manage.py migrate

# Collect static files
docker compose run --rm web python manage.py collectstatic --noinput

# Create superuser (for admin access)
docker compose run --rm web python manage.py createsuperuser

# Start services
docker compose up -d
```

### 6. Verify Deployment

```bash
# Check running containers
docker compose ps

# Check logs
docker compose logs -f

# Test the application
curl http://localhost
```

---

## Updating the Application

### Quick Update (Recommended)

Use the automated deployment script:

```bash
cd /opt/meu-financeiro
./scripts/deploy.sh
```

This script automatically:
1. Pulls latest code from Git
2. Builds new Docker images
3. Runs database migrations
4. Collects static files
5. Restarts containers
6. Cleans up old images

### Manual Update Process

If you prefer manual control:

```bash
cd /opt/meu-financeiro

# 1. Pull latest code
git pull origin master

# 2. Rebuild Docker images
docker compose build

# 3. Run database migrations
docker compose run --rm web python manage.py migrate --noinput

# 4. Collect static files
docker compose run --rm web python manage.py collectstatic --noinput

# 5. Restart containers
docker compose down
docker compose up -d

# 6. Clean up old images
docker image prune -f
```

### Update with Zero Downtime

For production environments requiring zero downtime:

```bash
cd /opt/meu-financeiro

# Pull latest code
git pull origin master

# Build new images
docker compose build

# Run migrations (safe to run while app is running)
docker compose run --rm web python manage.py migrate --noinput

# Collect static files
docker compose run --rm web python manage.py collectstatic --noinput

# Graceful restart (one container at a time)
docker compose up -d --no-deps --build web
docker compose up -d --no-deps nginx
```

### Rolling Back to Previous Version

```bash
cd /opt/meu-financeiro

# View commit history
git log --oneline -10

# Rollback to specific commit
git checkout <commit-hash>

# Rebuild and restart
docker compose build
docker compose up -d
```

---

## Database Management

### Backup Database

Using the automated backup script:

```bash
cd /opt/meu-financeiro
./scripts/backup-supabase.sh
```

Backups are stored in `~/backups/` and automatically deleted after 7 days.

**Configure backup retention:**
```bash
# Keep backups for 30 days
RETENTION_DAYS=30 ./scripts/backup-supabase.sh
```

### Manual Database Backup

```bash
# Extract database credentials from .env
source .env

# Backup to file
docker compose run --rm web python manage.py dumpdata --indent=2 > backup_$(date +%Y%m%d).json

# Or use pg_dump for PostgreSQL
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# From Django dumpdata backup
docker compose run --rm web python manage.py loaddata backup_20251230.json

# From PostgreSQL dump
psql $DATABASE_URL < backup_20251230.sql
```

### Database Migration from SQLite to PostgreSQL

If migrating from local SQLite to production PostgreSQL:

```bash
# 1. On local machine with SQLite:
python manage.py dumpdata --indent=2 > db_backup.json

# 2. Copy backup to VPS
scp db_backup.json user@your-vps:/opt/meu-financeiro/

# 3. On VPS with PostgreSQL configured:
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py loaddata db_backup.json
```

See [CLAUDE.md](CLAUDE.md#database-migration-between-sqlite-and-postgresql) for detailed migration instructions.

### Run Django Management Commands

```bash
# Run any Django command
docker compose run --rm web python manage.py <command>

# Examples:
docker compose run --rm web python manage.py createsuperuser
docker compose run --rm web python manage.py recurrence_payment
docker compose run --rm web python manage.py import_csv /path/to/file.csv
docker compose run --rm web python manage.py dbshell
```

---

## SSL Certificate Setup

### Using Let's Encrypt (Certbot)

#### 1. Initial Certificate Generation

```bash
# Install Certbot
sudo apt install certbot -y

# Stop nginx temporarily
docker compose stop nginx

# Generate certificate
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email

# Restart nginx
docker compose up -d nginx
```

#### 2. Automatic Certificate Renewal

Let's Encrypt certificates expire after 90 days. Setup automatic renewal:

```bash
# Test renewal process
sudo certbot renew --dry-run

# Create renewal script
sudo nano /opt/renewal.sh
```

Add the following content:

```bash
#!/bin/bash
docker compose -f /opt/meu-financeiro/docker-compose.yml stop nginx
certbot renew --quiet
docker compose -f /opt/meu-financeiro/docker-compose.yml up -d nginx
```

Make it executable and add to crontab:

```bash
sudo chmod +x /opt/renewal.sh

# Add to crontab (runs daily at 3am)
sudo crontab -e

# Add this line:
0 3 * * * /opt/renewal.sh >> /var/log/certbot-renewal.log 2>&1
```

### Temporary HTTP-Only Setup

For testing before SSL setup:

1. Modify [docker-compose.yml](docker-compose.yml) to only expose port 80:
   ```yaml
   nginx:
     ports:
       - "80:80"
       # - "443:443"  # Comment out HTTPS
   ```

2. Modify [nginx/nginx.conf](nginx/nginx.conf) to disable HTTPS server block

3. Deploy with HTTP only

---

## Monitoring and Troubleshooting

### View Logs

```bash
# All containers
docker compose logs -f

# Specific container
docker compose logs -f web
docker compose logs -f nginx

# Last 100 lines
docker compose logs --tail=100 web
```

### Check Container Status

```bash
# View running containers
docker compose ps

# View resource usage
docker stats

# Check container health
docker inspect meu-financeiro-web-1 | grep -A 10 Health
```

### Access Django Shell

```bash
docker compose run --rm web python manage.py shell
```

### Access Database Shell

```bash
docker compose run --rm web python manage.py dbshell
```

### Common Issues

#### 1. Static Files Not Loading

```bash
# Recollect static files
docker compose run --rm web python manage.py collectstatic --noinput --clear
docker compose restart nginx
```

#### 2. Database Connection Errors

```bash
# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Test database connection
docker compose run --rm web python manage.py dbshell
```

#### 3. Permission Errors

```bash
# Fix staticfiles permissions
docker compose run --rm web chmod -R 755 /app/staticfiles
```

#### 4. Container Won't Start

```bash
# Check logs for errors
docker compose logs web

# Rebuild from scratch
docker compose down
docker compose build --no-cache
docker compose up -d
```

#### 5. Out of Disk Space

```bash
# Clean Docker resources
docker system prune -a --volumes

# Remove old images
docker image prune -a

# Check disk usage
df -h
du -sh /var/lib/docker
```

### Performance Monitoring

```bash
# Monitor Django queries (if SQL logging enabled)
docker compose logs web | grep "SELECT"

# Use Django performance command
docker compose run --rm web python manage.py measure_performance --iterations=5
```

---

## Backup and Restore

### Complete System Backup

```bash
#!/bin/bash
# Create full backup
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/$BACKUP_DATE"

mkdir -p $BACKUP_DIR

# Backup database
./scripts/backup-supabase.sh

# Backup code and configs
tar -czf $BACKUP_DIR/code.tar.gz \
  --exclude='venv' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  /opt/meu-financeiro

# Backup environment
cp /opt/meu-financeiro/.env $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### Automated Daily Backups

```bash
# Create backup script
sudo nano /opt/daily-backup.sh
```

```bash
#!/bin/bash
cd /opt/meu-financeiro
./scripts/backup-supabase.sh
```

```bash
# Make executable
sudo chmod +x /opt/daily-backup.sh

# Add to crontab (daily at 2am)
sudo crontab -e

# Add line:
0 2 * * * /opt/daily-backup.sh >> /var/log/backup.log 2>&1
```

### Disaster Recovery

Complete restore from backup:

```bash
# 1. Install fresh VPS (follow Initial VPS Setup)

# 2. Clone repository
cd /opt/meu-financeiro
git clone https://github.com/YOUR_USERNAME/meu-financeiro.git .

# 3. Restore environment file
cp /path/to/backup/.env .

# 4. Start services
docker compose up -d

# 5. Restore database
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py loaddata /path/to/backup.json

# 6. Restore SSL certificates
sudo cp -r /path/to/letsencrypt/backup /etc/letsencrypt
```

---

## Production Checklist

Before going live, verify:

- [ ] `DEBUG=false` in .env
- [ ] Strong `SECRET_KEY` generated
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] `CSRF_TRUSTED_ORIGINS` includes HTTPS URLs
- [ ] Database backups scheduled (daily)
- [ ] SSL certificate installed and auto-renewal configured
- [ ] Firewall configured (ports 22, 80, 443)
- [ ] Monitoring/logging configured
- [ ] Superuser account created
- [ ] Application accessible via HTTPS
- [ ] Static files loading correctly
- [ ] Email notifications tested (if applicable)

---

## Quick Reference

### Essential Commands

```bash
# Update application
cd /opt/meu-financeiro && ./scripts/deploy.sh

# View logs
docker compose logs -f web

# Restart application
docker compose restart web

# Backup database
./scripts/backup-supabase.sh

# Access Django shell
docker compose run --rm web python manage.py shell

# Create superuser
docker compose run --rm web python manage.py createsuperuser

# Check status
docker compose ps
```

### File Locations

- Application: `/opt/meu-financeiro`
- Environment config: `/opt/meu-financeiro/.env`
- Database backups: `~/backups/`
- SSL certificates: `/etc/letsencrypt/live/your-domain.com/`
- Nginx config: `/opt/meu-financeiro/nginx/nginx.conf`
- Docker compose: `/opt/meu-financeiro/docker-compose.yml`

---

## Additional Resources

- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Docker Documentation](https://docs.docker.com/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Project README](CLAUDE.md) - Development guide and architecture

---

## Support

For issues or questions:
1. Check the logs: `docker compose logs -f`
2. Review [CLAUDE.md](CLAUDE.md) for development patterns
3. Check Docker status: `docker compose ps`
4. Review database connection: Test DATABASE_URL

## License

This deployment guide is part of the Meu Financeiro project.
