# Database Backup & Restore Guide

Complete guide for backing up and restoring the Meu Financeiro database.

## Table of Contents
- [Backup Methods](#backup-methods)
- [Restore Methods](#restore-methods)
- [Automated Scripts](#automated-scripts)
- [Best Practices](#best-practices)

## Backup Methods

### 1. Django Backup (Recommended for Migration)

Django's `dumpdata` creates database-agnostic JSON backups that work across SQLite and PostgreSQL.

```bash
# Full backup (all data)
python manage.py dumpdata --indent=2 > backup.json

# Clean backup (exclude sessions, permissions)
python manage.py dumpdata \
    --exclude auth.permission \
    --exclude contenttypes \
    --exclude admin.logentry \
    --exclude sessions.session \
    --indent=2 > backup_clean.json

# Backup specific apps only
python manage.py dumpdata registers reports --indent=2 > backup_data.json

# Compress backup
gzip backup.json
```

**Pros:**
- Database-agnostic (works with SQLite and PostgreSQL)
- Human-readable JSON format
- Easy to inspect and edit

**Cons:**
- Larger file size
- Slower for very large databases

### 2. PostgreSQL Native Backup

Direct PostgreSQL dump for production databases.

```bash
# Set password (or use .env)
export PGPASSWORD="username@2025"

# Binary dump (smaller, faster)
pg_dump -h aws-1-us-east-2.pooler.supabase.com \
        -p 6543 \
        -U postgres.mzfjjcytrpxdfcqseeof \
        -d postgres \
        -F c \
        -f backup.dump

# SQL dump (readable)
pg_dump -h aws-1-us-east-2.pooler.supabase.com \
        -p 6543 \
        -U postgres.mzfjjcytrpxdfcqseeof \
        -d postgres \
        -f backup.sql

# Data only (no schema)
pg_dump -h aws-1-us-east-2.pooler.supabase.com \
        -p 6543 \
        -U postgres.mzfjjcytrpxdfcqseeof \
        -d postgres \
        --data-only \
        -f backup_data.sql
```

**Pros:**
- Fast and efficient
- Smaller file size
- Preserves PostgreSQL-specific features

**Cons:**
- PostgreSQL-only (won't work with SQLite)
- Less human-readable (binary format)

## Restore Methods

### 1. Django Restore

```bash
# Optional: Flush database first
python manage.py flush --no-input

# Load from backup
python manage.py loaddata backup.json

# Or from compressed
gunzip -c backup.json.gz | python manage.py loaddata --format=json -
```

### 2. PostgreSQL Restore

```bash
export PGPASSWORD="username@2025"

# Restore from dump
pg_restore -h aws-1-us-east-2.pooler.supabase.com \
           -p 6543 \
           -U postgres.mzfjjcytrpxdfcqseeof \
           -d postgres \
           --clean \
           --if-exists \
           backup.dump

# Restore from SQL
psql -h aws-1-us-east-2.pooler.supabase.com \
     -p 6543 \
     -U postgres.mzfjjcytrpxdfcqseeof \
     -d postgres \
     -f backup.sql
```

## Automated Scripts

### Backup Script

```bash
# Django backup (default)
./backup_production.sh django

# PostgreSQL backup
./backup_production.sh postgres

# Both backups
./backup_production.sh both
```

The script will:
- Create `backups/` directory if needed
- Generate timestamped backup files
- Compress Django backups with gzip
- Display file sizes
- Handle errors gracefully

### Restore Script

```bash
# Restore from backup
./restore_backup.sh backups/django_backup_20250101_120000.json.gz

# Or from PostgreSQL dump
./restore_backup.sh backups/postgres_backup_20250101_120000.dump
```

The script will:
- Detect backup format automatically
- Decompress if needed
- Prompt for confirmation (safety check)
- Optionally flush database before restore
- Display success/error messages

## Best Practices

### Regular Backups

1. **Before Major Changes**
   ```bash
   ./backup_production.sh both
   ```

2. **Before Migrations**
   ```bash
   python manage.py dumpdata --indent=2 > backup_pre_migration.json
   ```

3. **Scheduled Backups** (via cron)
   ```bash
   # Daily at 2 AM
   0 2 * * * cd /path/to/meu-financeiro && ./backup_production.sh django
   ```

### Backup Storage

1. **Local Backups** - Keep in `backups/` directory (gitignored)
2. **Remote Backups** - Upload to cloud storage
   ```bash
   # Example: Upload to Google Drive, S3, etc.
   rclone copy backups/ remote:meu-financeiro-backups/
   ```

3. **Retention Policy**
   - Keep daily backups for 7 days
   - Keep weekly backups for 1 month
   - Keep monthly backups for 1 year

### Backup Verification

Always test your backups:

```bash
# 1. Create test backup
./backup_production.sh django

# 2. Restore to local SQLite (test)
# Comment out DATABASE_URL in .env
python manage.py migrate
./restore_backup.sh backups/django_backup_*.json.gz

# 3. Verify data
python manage.py runserver
# Check data via web interface

# 4. Restore DATABASE_URL
# Uncomment DATABASE_URL in .env
```

## Migration Workflow

### PostgreSQL → SQLite (Local Development)

```bash
# 1. Backup production
./backup_production.sh django

# 2. Remove/comment DATABASE_URL in .env
# DATABASE_URL=postgresql://...

# 3. Setup local SQLite
rm -f db.sqlite3
python manage.py migrate

# 4. Restore data
./restore_backup.sh backups/django_backup_YYYYMMDD_HHMMSS.json.gz

# 5. Test
python manage.py runserver
```

### SQLite → PostgreSQL (Production)

```bash
# 1. Backup SQLite
python manage.py dumpdata --indent=2 > backup_sqlite.json

# 2. Add DATABASE_URL to .env
DATABASE_URL=postgresql://user:pass@host:port/db

# 3. Run migrations on PostgreSQL
python manage.py migrate

# 4. Load data
python manage.py loaddata backup_sqlite.json

# 5. Verify
python manage.py runserver
```

## Troubleshooting

### Issue: "Permission denied"
```bash
chmod +x backup_production.sh restore_backup.sh
```

### Issue: "pg_dump: command not found"
```bash
# Install PostgreSQL client tools
sudo apt-get install postgresql-client
```

### Issue: "Connection refused"
- Check DATABASE_URL in `.env`
- Verify network connectivity
- Check if using pooler port (6543) vs direct port (5432)

### Issue: "Duplicate key error" during restore
```bash
# Flush database before restore
python manage.py flush --no-input
# Then restore again
```

## Security Notes

⚠️ **Important:**
- Never commit backup files to git (already in `.gitignore`)
- Store backups securely (encrypt sensitive data)
- Rotate credentials regularly
- Use environment variables for passwords
- Restrict backup file permissions:
  ```bash
  chmod 600 backups/*
  ```

## Quick Reference

| Task | Command |
|------|---------|
| Quick Django backup | `./backup_production.sh` |
| PostgreSQL backup | `./backup_production.sh postgres` |
| Both backups | `./backup_production.sh both` |
| Restore Django backup | `./restore_backup.sh backups/django_backup_*.json.gz` |
| Restore PostgreSQL dump | `./restore_backup.sh backups/postgres_backup_*.dump` |
| List backups | `ls -lh backups/` |
| Compress backup | `gzip backup.json` |
| Decompress | `gunzip backup.json.gz` |
