# Meu Financeiro

[![CI/CD](https://github.com/jrneliodias/meu-financeiro/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/jrneliodias/meu-financeiro/actions/workflows/ci-cd.yml)

A production personal finance management platform built with Django and PostgreSQL. Track expenses, income, installment plans, and recurring payments with an optimized reporting dashboard.

**Live demo:** [meu-financeiro.tec.br](https://meu-financeiro.tec.br)

---

## Features

- **Expense & income tracking** — categorized records with payment method attribution
- **Installment plans** — multi-payment purchases that auto-generate monthly expense records
- **Recurring expenses** — monthly automation via management command (`recurrence_payment`)
- **Credit card billing cycles** — billing period calculations per card with cutoff-date awareness
- **Financial reports dashboard** — monthly summaries, category breakdowns, daily spending trends
- **Bank statement import** — bulk CSV import from Nubank exports with automatic record classification
- **Investment tracking** — portfolio records with asset categorization

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Django 4 |
| Database | PostgreSQL (production), SQLite (local dev) |
| Frontend | Django Templates, JavaScript |
| Infrastructure | Docker, Nginx, VPS (Ubuntu) |
| CI/CD | GitHub Actions |
| Static files | WhiteNoise |

---

## Architecture

The codebase uses a layered architecture with clear separation of concerns:

### Service Layer
Business logic is decoupled from views into dedicated service classes. Views delegate all domain operations to services, keeping them thin and testable.

```
registers/services/
├── ExpenseService       # expense creation, editing, validation
├── IncomeService        # income management
├── InstallmentService   # multi-payment plan handling
└── CSVImportService     # bulk import orchestration
```

### Repository Pattern
Complex database queries are isolated in repository classes, using `select_related` and aggregated queries to eliminate N+1 problems. Report pages that previously issued 50+ queries now run in 3–5.

```
reports/repository/
├── ExpenseRepository    # optimized monthly expense queries
├── CategoryRepository   # category aggregation
├── PaymentMethodRepository
└── IncomeRepository
```

### Strategy Pattern — CSV Import
The CSV import pipeline uses a strategy pattern to classify each record type, making it extensible without modifying existing code.

```
RecordStrategyFactory
├── ExplicitTypeStrategy         # 'type' column takes precedence
├── NegativeAmountExpenseStrategy # negative amount → Expense
└── PositiveAmountIncomeStrategy  # positive amount → Income
```

### Component Pattern — Forms
Form components use dependency injection via `kwargs.pop('user')` to configure fields with user-scoped context (e.g., populating payment method dropdowns with the user's own accounts).

---

## Local Setup

```bash
git clone https://github.com/jrneliodias/meu-financeiro.git
cd meu-financeiro

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill in SECRET_KEY and other vars

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The app runs on SQLite by default. Set `DATABASE_URL` in `.env` to switch to PostgreSQL.

---

## Running Tests

```bash
# All tests
python manage.py test

# Specific app
python manage.py test registers
python manage.py test reports

# Single test class
python manage.py test registers.tests.test_csv_record_strategies.NegativeAmountExpenseStrategyTest
```

---

## CI/CD Pipeline

Every push to `master` triggers a GitHub Actions workflow that:

1. Runs the full test suite against a PostgreSQL service container
2. On success, SSHs into the VPS and runs `scripts/deploy.sh`

The deploy script pulls the latest image, runs migrations, and restarts the Nginx + Gunicorn stack via Docker Compose.

See [DEPLOY.md](DEPLOY.md) for the full infrastructure setup (Docker, Nginx, SSL, environment configuration).

---

## CSV Import

The platform accepts bank statement exports from Nubank in CSV format:

```csv
date,description,amount,category,type,payment_method
2025-09-02,Uber *Trip,8.96,Transport,expense,Crédito - Nubank
```

Import via the web interface at `/register/csv-import` or via the management command:

```bash
python manage.py import_csv path/to/statement.csv
```
