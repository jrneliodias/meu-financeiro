#!/bin/bash
set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}==> Iniciando deploy...${NC}"

# Verifica se estamos no diretorio correto
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Erro: docker-compose.yml nao encontrado. Execute este script na raiz do projeto.${NC}"
    exit 1
fi

# Pull do codigo mais recente
echo -e "${YELLOW}==> Atualizando codigo...${NC}"
git pull origin master

# Build das imagens Docker
echo -e "${YELLOW}==> Construindo imagens Docker...${NC}"
docker compose build

# Executa migrations no mesmo container para o arquivo gerado pelo makemigrations
# ser visivel pelo migrate
echo -e "${YELLOW}==> Criando e executando migrations...${NC}"
docker compose run --rm web sh -c "python manage.py makemigrations --noinput && python manage.py migrate --noinput"

# Coleta static files
echo -e "${YELLOW}==> Coletando arquivos estaticos...${NC}"
docker compose run --rm web python manage.py collectstatic --noinput

# Reinicia containers
echo -e "${YELLOW}==> Reiniciando containers...${NC}"
docker compose up -d

# Limpa imagens antigas
echo -e "${YELLOW}==> Limpando imagens nao utilizadas...${NC}"
docker image prune -f

# Status final
echo -e "${GREEN}==> Deploy concluido com sucesso!${NC}"
echo ""
docker compose ps
