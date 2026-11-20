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

Domain rules live on the models; each feature keeps its views, logic and templates together.

```
registers/models.py      # models + rules: billing month (ExpenseQuerySet), recurring occurrences, installment plans
registers/views/         # data entry, one module per feature (expenses, incomes, presets, estimates, CSV)
registers/csv/           # importer (standard CSV → expenses/incomes) and processor (Nubank → standard CSV)
reports/services/        # dashboard numbers per feature: summary, budget, installments, recurring, categories, daily
reports/views/           # dashboard tabs, expense list, recurring expenses and the month's payments
utils/                   # dates, money formatting, small HTTP helpers
```

- Every query is scoped to the logged-in user.
- Dashboard aggregations are single grouped queries (`Expense.objects.filter(user=…).in_billing_year(year)…`).
- Money is formatted once, on the server (`|format_brl`); JS receives numbers via `json_script`.

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
# All tests (unset DATABASE_URL so they run on SQLite)
DATABASE_URL= python manage.py test

# Specific app / module
DATABASE_URL= python manage.py test registers
DATABASE_URL= python manage.py test registers.tests.test_csv_import
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
