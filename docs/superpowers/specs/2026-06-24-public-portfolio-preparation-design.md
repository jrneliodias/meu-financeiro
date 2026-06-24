---
name: public-portfolio-preparation
description: Design for preparing the Meu Financeiro project for public GitHub visibility and recruiter evaluation
metadata:
  type: project
---

# Design: Preparação do Projeto para Portfolio Público

**Data:** 2026-06-24  
**Objetivo:** Tornar o repositório seguro e profissional para avaliação de recrutadores

---

## Contexto

O projeto Meu Financeiro é uma aplicação Django de gestão financeira pessoal com deploy em produção. O repositório contém atualmente dados pessoais sensíveis rastreados no histórico git (extratos bancários reais, banco de dados SQLite) e arquivos de desenvolvimento avulsos que poluem a raiz do projeto. O objetivo é preparar o repositório para visibilidade pública sem expor dados pessoais, e criar um README que destaque a maturidade técnica do projeto para recrutadores.

---

## Seção 1 — Remoção de Dados Sensíveis do Histórico Git

### Problema

Os seguintes arquivos com dados pessoais reais estão rastreados no git e presentes no histórico de commits:

- `csvs/` — extratos reais de transações Nubank (múltiplos arquivos CSV)
- `db.sqlite3`, `db.sqlite3.bak` — banco de dados local com dados pessoais
- `db.json`, `db_backup.json`, `db_sqlite_backup.json` — dumps com dados reais
- `backup_production_20251231_203959.json` — backup de produção

### Solução

Usar `git filter-branch --index-filter` para reescrever todo o histórico e eliminar esses arquivos de todos os commits. Após a limpeza, fazer `git push --force` para atualizar o repositório remoto.

### .gitignore — Adições

```
db.sqlite3
db.sqlite3.bak
csvs/
db*.json
backup*.json
```

---

## Seção 2 — Limpeza do Diretório Raiz

### Arquivos a remover do repositório (git rm + delete)

| Arquivo | Motivo |
|---|---|
| `new-feature.md` | Nota interna de desenvolvimento |
| `process_pix_payment.md` | Rascunho de processo interno |
| `billing-cycles-refactor-report.md` | Relatório interno de refactor |
| `PERFORMANCE_FIX_SUMMARY.md` | Sumário interno de otimização |
| `PERFORMANCE_OPTIMIZATION_PROMPT.md` | Prompt de IA interno |
| `gemini_process.py` | Script utilitário avulso sem contexto |
| `scripts/clear_cache_and_test.py` | Script de desenvolvimento local avulso |
| `scripts/convert_csv_datetime.py` | Script utilitário de migração de dados |
| `scripts/final_performance_test.py` | Script de teste de performance local |
| `scripts/performance_measurement.py` | Script de medição local |
| `scripts/print_categories.py` | Script utilitário avulso |
| `scripts/process_csv.py` | Script de processamento de CSV local |
| `scripts/remove_columns.py` | Script utilitário avulso |
| `scripts/replace_dash_pattern.py` | Script utilitário avulso |
| `scripts/replace_dash_simple.py` | Script utilitário avulso |
| `scripts/test_admin_performance.py` | Script de teste local |
| `scripts/test_billing_calculator.py` | Script de teste local |
| `scripts/test_calc.py` | Script de teste local |
| `scripts/test_csv_import.py` | Script de teste local |
| `scripts/backup-supabase.sh` | Script de backup operacional (pode manter se quiser mostrar ops) |

**Manter obrigatoriamente:** `scripts/deploy.sh` — referenciado pelo `ci-cd.yml`|

### Arquivos a manter

- `DEPLOY.md` — documenta infraestrutura Docker + VPS + SSL (mostra maturidade)
- `Dockerfile`, `docker-compose.yml`, `nginx/` — containerização profissional
- `.github/workflows/` — CI/CD configurado com GitHub Actions
- `requirements.txt`, `Procfile`, `.env.example` — setup padrão
- `BACKUP_GUIDE.md` — documentação operacional
- `docs/` — specs e guias do projeto

---

## Seção 3 — README.md

Criar `README.md` na raiz com as seguintes seções:

1. **Título + Descrição** — o que é o projeto em 2 linhas
2. **Link da demo ao vivo** — `https://meu-financeiro.tec.br`
3. **Funcionalidades** — lista das principais features
4. **Stack** — Python 3, Django, PostgreSQL, Docker, Nginx, GitHub Actions
5. **Arquitetura** — destaque dos padrões técnicos:
   - Service layer (lógica desacoplada das views)
   - Repository pattern (queries otimizadas, N+1 eliminado)
   - Strategy pattern (importação CSV extensível)
   - Component pattern (formulários com injeção de contexto)
6. **Setup local** — clone, configurar .env, migrate, runserver
7. **Testes** — como rodar a suite de testes
8. **CI/CD** — badge do GitHub Actions

### Idioma

README em inglês — padrão para projetos públicos avaliados por recrutadores que podem ser internacionais.

---

## Ordem de Execução

1. Fazer backup local antes de reescrever histórico
2. Remover dados sensíveis com `git filter-branch`
3. Atualizar `.gitignore`
4. Remover arquivos de desenvolvimento avulsos
5. Criar `README.md`
6. Fazer `git push --force` para o repositório remoto

---

## Riscos

- **Reescrita de histórico é irreversível** — fazer backup antes (`git bundle`)
- **Push force em repositório público** — se já houver forks ou colaboradores, eles precisarão rebasear. Neste caso é repositório pessoal, risco baixo.
