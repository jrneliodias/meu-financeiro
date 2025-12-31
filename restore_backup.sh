#!/bin/bash
#
# Database Restore Script
# Usage: ./restore_backup.sh <backup_file>
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh backups/ 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}=== Database Restore ===${NC}"
echo "Backup file: $BACKUP_FILE"
echo ""

# Detect backup type by extension
if [[ "$BACKUP_FILE" == *.json.gz ]]; then
    echo -e "${BLUE}Detected compressed Django backup${NC}"

    # Decompress first
    TEMP_FILE="${BACKUP_FILE%.gz}"
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    BACKUP_FILE="$TEMP_FILE"
fi

if [[ "$BACKUP_FILE" == *.json ]]; then
    echo -e "${BLUE}Restoring Django backup...${NC}"

    # Warning
    echo -e "${YELLOW}⚠ WARNING: This will overwrite existing data!${NC}"
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo "Restore cancelled."
        exit 0
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Optional: flush database first
    read -p "Do you want to flush the database first? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        echo -e "${BLUE}Flushing database...${NC}"
        python manage.py flush --no-input
    fi

    # Load data
    echo -e "${BLUE}Loading data from backup...${NC}"
    python manage.py loaddata "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Django restore completed successfully${NC}"
    else
        echo -e "${RED}✗ Django restore failed${NC}"
        exit 1
    fi

    # Clean up temp file if it was decompressed
    if [[ "$1" == *.json.gz ]]; then
        rm -f "$TEMP_FILE"
    fi

elif [[ "$BACKUP_FILE" == *.dump ]]; then
    echo -e "${BLUE}Restoring PostgreSQL dump backup...${NC}"

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

    # Extract connection details
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    DB_PASS=$(echo $DATABASE_URL | sed -n 's/.*\/\/[^:]*:\([^@]*\)@.*/\1/p')
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

    # Warning
    echo -e "${YELLOW}⚠ WARNING: This will overwrite the production database!${NC}"
    echo "Database: $DB_HOST:$DB_PORT/$DB_NAME"
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo "Restore cancelled."
        exit 0
    fi

    export PGPASSWORD="$DB_PASS"

    pg_restore -h "$DB_HOST" \
               -p "$DB_PORT" \
               -U "$DB_USER" \
               -d "$DB_NAME" \
               --clean \
               --if-exists \
               "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PostgreSQL restore completed successfully${NC}"
    else
        echo -e "${RED}✗ PostgreSQL restore failed${NC}"
        exit 1
    fi

    unset PGPASSWORD

elif [[ "$BACKUP_FILE" == *.sql ]]; then
    echo -e "${BLUE}Restoring PostgreSQL SQL backup...${NC}"

    # Check if DATABASE_URL is set
    if [ -z "$DATABASE_URL" ]; then
        if [ -f .env ]; then
            export $(grep DATABASE_URL .env | xargs)
        else
            echo -e "${RED}✗ DATABASE_URL not found${NC}"
            exit 1
        fi
    fi

    # Extract connection details
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    DB_PASS=$(echo $DATABASE_URL | sed -n 's/.*\/\/[^:]*:\([^@]*\)@.*/\1/p')
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

    # Warning
    echo -e "${YELLOW}⚠ WARNING: This will overwrite the production database!${NC}"
    echo "Database: $DB_HOST:$DB_PORT/$DB_NAME"
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo "Restore cancelled."
        exit 0
    fi

    export PGPASSWORD="$DB_PASS"

    psql -h "$DB_HOST" \
         -p "$DB_PORT" \
         -U "$DB_USER" \
         -d "$DB_NAME" \
         -f "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PostgreSQL restore completed successfully${NC}"
    else
        echo -e "${RED}✗ PostgreSQL restore failed${NC}"
        exit 1
    fi

    unset PGPASSWORD

else
    echo -e "${RED}Error: Unknown backup file format${NC}"
    echo "Supported formats: .json, .json.gz, .dump, .sql"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Restore Complete ===${NC}"
