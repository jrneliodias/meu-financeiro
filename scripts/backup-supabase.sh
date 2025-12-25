#!/bin/bash
set -e

# Configuracoes
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/meufinanceiro_$DATE.sql"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Cria diretorio de backup se nao existir
mkdir -p "$BACKUP_DIR"

# Carrega variaveis do .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Erro: Arquivo .env nao encontrado em $ENV_FILE${NC}"
    exit 1
fi

# Extrai credenciais do DATABASE_URL
# Formato: postgresql://user:password@host:port/database
DATABASE_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d '=' -f2-)

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Erro: DATABASE_URL nao encontrada no .env${NC}"
    exit 1
fi

# Parse do DATABASE_URL
DB_USER=$(echo "$DATABASE_URL" | sed -n 's|postgresql://\([^:]*\):.*|\1|p')
DB_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's|postgresql://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|postgresql://[^@]*@\([^:]*\):.*|\1|p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|postgresql://[^@]*@[^:]*:\([^/]*\)/.*|\1|p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|postgresql://[^/]*/\(.*\)|\1|p')

echo -e "${YELLOW}==> Iniciando backup do banco de dados...${NC}"
echo "Host: $DB_HOST"
echo "Database: $DB_NAME"
echo "Destino: $BACKUP_FILE"

# Executa pg_dump
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    > "$BACKUP_FILE"

# Verifica se o backup foi criado
if [ ! -s "$BACKUP_FILE" ]; then
    echo -e "${RED}Erro: Backup vazio ou falhou${NC}"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Comprime o backup
echo -e "${YELLOW}==> Comprimindo backup...${NC}"
gzip "$BACKUP_FILE"

# Remove backups antigos
echo -e "${YELLOW}==> Removendo backups com mais de $RETENTION_DAYS dias...${NC}"
find "$BACKUP_DIR" -name "meufinanceiro_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Lista backups existentes
echo -e "${GREEN}==> Backup concluido: ${BACKUP_FILE}.gz${NC}"
echo ""
echo "Backups disponiveis:"
ls -lh "$BACKUP_DIR"/meufinanceiro_*.sql.gz 2>/dev/null || echo "Nenhum backup encontrado"
