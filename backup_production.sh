#!/bin/bash
#
# Production Database Backup Script
# Usage: ./backup_production.sh [django|postgres|both]
#

set -e  # Exit on error

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_TYPE=${1:-django}  # Default to django backup

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}=== Production Database Backup ===${NC}"
echo "Backup type: $BACKUP_TYPE"
echo "Timestamp: $TIMESTAMP"
echo ""

# Function to create Django backup
django_backup() {
    echo -e "${BLUE}Creating Django backup...${NC}"

    # Activate virtual environment
    source venv/bin/activate

    # Create backup file
    BACKUP_FILE="$BACKUP_DIR/django_backup_${TIMESTAMP}.json"

    python manage.py dumpdata \
        --exclude auth.permission \
        --exclude contenttypes \
        --exclude admin.logentry \
        --exclude sessions.session \
        --indent=2 \
        > "$BACKUP_FILE"

    # Check if successful
    if [ $? -eq 0 ]; then
        FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✓ Django backup created: $BACKUP_FILE ($FILESIZE)${NC}"

        # Compress backup
        gzip "$BACKUP_FILE"
        COMPRESSED_SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
        echo -e "${GREEN}✓ Compressed to: $BACKUP_FILE.gz ($COMPRESSED_SIZE)${NC}"
    else
        echo -e "${RED}✗ Django backup failed${NC}"
        exit 1
    fi
}

# Function to create PostgreSQL backup
postgres_backup() {
    echo -e "${BLUE}Creating PostgreSQL backup...${NC}"

    # Check if DATABASE_URL is set
    if [ -z "$DATABASE_URL" ]; then
        # Try to load from .env
        if [ -f .env ]; then
            export $(grep DATABASE_URL .env | xargs)
        else
            echo -e "${RED}✗ DATABASE_URL not found${NC}"
            exit 1
        fi
    fi

    # Extract connection details from DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    DB_PASS=$(echo $DATABASE_URL | sed -n 's/.*\/\/[^:]*:\([^@]*\)@.*/\1/p')
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

    BACKUP_FILE="$BACKUP_DIR/postgres_backup_${TIMESTAMP}.dump"

    export PGPASSWORD="$DB_PASS"

    pg_dump -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            -F c \
            -f "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✓ PostgreSQL backup created: $BACKUP_FILE ($FILESIZE)${NC}"
    else
        echo -e "${RED}✗ PostgreSQL backup failed${NC}"
        exit 1
    fi

    unset PGPASSWORD
}

# Execute backup based on type
case "$BACKUP_TYPE" in
    django)
        django_backup
        ;;
    postgres)
        postgres_backup
        ;;
    both)
        django_backup
        echo ""
        postgres_backup
        ;;
    *)
        echo -e "${RED}Invalid backup type: $BACKUP_TYPE${NC}"
        echo "Usage: $0 [django|postgres|both]"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=== Backup Complete ===${NC}"
echo "Backup location: $BACKUP_DIR/"
ls -lh "$BACKUP_DIR/" | tail -n 3
