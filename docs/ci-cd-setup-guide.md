# Guia de Setup CI/CD — Django + Docker + VPS

Lições aprendidas durante a configuração deste projeto.

---

## 1. Estrutura do Workflow

```yaml
on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  test:   # roda em push e PR
  deploy: # roda só em push para master, após os testes passarem
    needs: test
    if: github.ref == 'refs/heads/master' && github.event_name == 'push'
```

---

## 2. Testes com PostgreSQL no CI

**Problema:** SQLite antigo do runner não suporta `CREATE INDEX IF NOT EXISTS` e `DROP COLUMN IF EXISTS` (PostgreSQL-specific SQL nas migrations).

**Solução:** Adicionar service container de PostgreSQL:

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_DB: test_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
    ports:
      - 5432:5432
env:
  DATABASE_URL: "postgresql://postgres:postgres@localhost:5432/test_db"
  DB_SSL_REQUIRE: "false"
```

**Atenção:** `psycopg3` tenta SSL por padrão. O container de CI não tem SSL. Solução:
- No `settings.py`: `ssl_require=os.getenv("DB_SSL_REQUIRE", "true").lower() == "true"`
- No workflow: `DB_SSL_REQUIRE: "false"`

---

## 3. Conflito de módulo `tests.py` vs `tests/`

**Problema:** Django gera `app/tests.py` por padrão. Se depois criar `app/tests/` com `__init__.py`, ambos coexistem e causam `ImportError`.

**Solução:** Apagar o `tests.py` placeholder quando usar a pasta `tests/`:
```bash
rm registers/tests.py
```

---

## 4. Variáveis de Ambiente Mínimas para Testes

```yaml
env:
  SECRET_KEY: "ci-secret-key-for-testing"
  DEBUG: "true"
  ALLOWED_HOSTS: "localhost,127.0.0.1,testserver"
  DATABASE_URL: "postgresql://postgres:postgres@localhost:5432/test_db"
  DB_SSL_REQUIRE: "false"
```

---

## 5. Deploy via SSH com `appleboy/ssh-action`

```yaml
- uses: appleboy/ssh-action@v1.2.0
  with:
    host: ${{ secrets.VPS_HOST }}
    username: ${{ secrets.VPS_USER }}
    key: ${{ secrets.VPS_SSH_KEY }}
    port: 22022          # porta não padrão da VPS
    envs: ENV_FILE
    script: |
      printf '%s' "$ENV_FILE" > /caminho/projeto/.env
      cd /caminho/projeto && bash scripts/deploy.sh
  env:
    ENV_FILE: ${{ secrets.ENV_FILE }}
```

**Atenção no script remoto:**
- Escrever o `.env` **antes** de rodar o deploy
- Usar `cd /caminho/projeto` antes de `bash scripts/deploy.sh` — o `deploy.sh` verifica se `docker-compose.yml` existe no diretório atual

---

## 6. Secrets necessários (Environment: PROD)

| Secret | Valor |
|--------|-------|
| `VPS_HOST` | IP ou domínio da VPS |
| `VPS_USER` | Usuário SSH (ex: `deploy`) |
| `VPS_SSH_KEY` | Conteúdo completo da chave privada (com `-----BEGIN` e `-----END`) |
| `ENV_FILE` | Conteúdo completo do `.env` de produção |

---

## 7. Chave SSH — Erros comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `ssh: no key found` | Secret `VPS_SSH_KEY` vazio ou sem cabeçalho PEM | Copiar chave privada completa incluindo `-----BEGIN/END-----` |
| `unable to authenticate` | Chave privada não tem o par público em `authorized_keys` na VPS | Adicionar a chave pública correspondente em `~/.ssh/authorized_keys` na VPS |

**Como identificar a chave correta:**
```bash
# Na VPS — ver quais chaves estão autorizadas
cat ~/.ssh/authorized_keys

# Na máquina local — listar chaves públicas
for f in ~/.ssh/*.pub; do echo "=== $f ==="; cat "$f"; done
```

**Gerar nova chave dedicada ao CI/CD:**
```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_deploy -N ""
# Autorizar na VPS:
ssh-copy-id -i ~/.ssh/github_actions_deploy.pub -p PORTA USUARIO@HOST
# Colocar a privada no secret VPS_SSH_KEY:
cat ~/.ssh/github_actions_deploy
```

---

## 8. Preparar a VPS antes do primeiro deploy

```bash
# O projeto precisa estar clonado na VPS antes do CI/CD funcionar
mkdir -p /caminho/
cd /caminho/
git clone git@github.com:usuario/repositorio.git nome-projeto

# Se repositório privado, a VPS precisa de acesso ao GitHub:
ssh -T git@github.com
# Se falhar, adicionar deploy key no repositório
```

---

## 9. Erro 400 após deploy

**Causa:** `ALLOWED_HOSTS` no `.env` de produção não inclui o domínio/IP sendo acessado.

**Checklist do `ENV_FILE` secret:**
```
DEBUG=false
SECRET_KEY=chave-super-secreta-de-producao
ALLOWED_HOSTS=meu-dominio.com.br,www.meu-dominio.com.br
DATABASE_URL=postgresql://usuario:senha@host:5432/banco
```

---

## 10. Testar o CI localmente antes de fazer push

```bash
# Subir PostgreSQL local para simular o CI
docker run --rm -d --name pg-test \
  -e POSTGRES_DB=test_db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:15

# Rodar os testes com as mesmas variáveis do CI
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db" \
DB_SSL_REQUIRE=false \
SECRET_KEY="ci-test-key" \
DEBUG=true \
ALLOWED_HOSTS="localhost,127.0.0.1,testserver" \
python manage.py test

# Derrubar o container
docker stop pg-test
```
