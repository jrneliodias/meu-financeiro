# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based personal finance management application called "Meu Financeiro" that helps users track expenses, income, investments, and generate financial reports.

## Architecture

### Apps
- **finance**: settings and root URLs (also routes the MCP endpoint in `registers/mcp_views.py`)
- **registers**: models, data entry (expense/income/recurring/presets/estimates), CSV import/processing
- **reports**: dashboard tabs, expense list, recurring expenses management and the month's payments
- **export**: monthly CSV export
- **utils**: helpers shared by every app (`dates`, `money`, `http`) and the shared template tags (`formatting`, `links`, `navigation`)
- `templates/` and `static/` (project level): the site chrome every app's pages extend

Dependency direction: `utils` ← `registers.models` ← everything else. `registers` never imports `reports`.

### Models (registers/models.py) own the domain rules
- `Expense.objects` is an `ExpenseQuerySet`: `in_billing_month(year, month)`, `in_billing_year(year)` (an expense dated before its payment method's `start_billing_day` belongs to the previous month's bill), `in_month(year, month)` (calendar month). This is the only definition of a billing period.
- `Expense.kind` / `kind_label` (installment, recurring or single).
- `RecurringExpense`: `charged_amount` (adds IOF when international), `due_date(y, m)` (day clamped to month end), `month_expense(y, m)`, `generate_for_month(y, m)` (at most one expense per calendar month), `sync_month_expense(y, m)`.
- `Installment.create_plan(...)` creates the plan and one expense per month.
- `RecurringExpense.objects.due_in(year, month)` (active and started by that month: the schedules that get an expense) and `.charged_total()` (IOF included).
- `Category.objects.expense()` / `.income()`; categories and payment methods are ordered by name (Meta).
- Every query in a view is scoped to `request.user`; another user's record is a 404.

### registers
- `views/` one module per feature (`expenses`, `incomes`, `recurring`, `presets`, `categories`, `budget_estimates`, `csv_import`, `csv_processor`); `urls.py` imports the modules directly.
- `forms.py`: forms own their fields, labels and validation; `StyledForm` gives widgets the app's Tailwind classes. Templates render each field with `register/components/form_field.html` (label, help, errors) and form-wide errors with `form_errors.html`; views don't flash field errors. `ExpenseForm` edits, `ExpenseCreateForm` adds installments, the recurring flag and quick-fill presets.
- `csv/importer.py` (standard CSV → Expense/Income: `type` column, else the amount's sign) and `csv/processor.py` (Nubank export → standard CSV, no DB writes).
- `budget_copy.py`: copy category estimates from the latest earlier month.

### reports
- `services/` one module per dashboard feature, each a set of functions taking `user`: `summary` (balance, spent today, yearly charts), `budget` (`monthly_budget` → BudgetSummary), `installments`, `recurring` (`month_overview`, `generate_month`, `set_paid`), `categories`, `daily`.
- `views/dashboard.py`: the five tabs (`/`, `/gastos/`, `/categorias/`, `/parcelas/`, `/despesas/`) and `/orcamento/detalhamento/`; each tab computes only what it shows. Templates in `reports/templates/reports/tabs/` (`_layout.html`, `_header.html`, `_nav.html`).
- `views/expense_list.py`: `/despesas/lista/` (`?date=` | `?category_id=[&month=&year=]` | `?installments=1&month=&year=`, `back=` returns to the origin). Build links to it with `{% url_returning 'expense_list_page' … %}` (templatetags/links.py).
- `views/recurring.py`: recurring list/edit/delete/toggle, `/recurring-expenses/processar/`, `/recurring-payments/`, the bell pop-up (`payment_notifications`) and the paid checkbox endpoint.
- Modals only for confirmations; lists and edits are pages.

### Templates and JS
- Site chrome lives at project level: `templates/core/base.html` (sidebar via `{% sidebar_nav %}` from `utils/templatetags/navigation.py`, flash messages in `core/messages.html`, the bell once per page — dashboard tabs move it to the header via the `sidebar_bell` block), `templates/auth/login.html`, and `static/` (`js/app.js`, `js/tailwind_config.js`, `css/typography.css`).
- Money is formatted on the server with `{{ value|format_brl }}` (`{% load formatting %}`, backed by `utils/money.py`); month names come from `{% month_choices %}` (Django's translated `MONTHS`). Services return numbers, never formatted strings.
- Strings JS shows come from the template (`data-*` rendered with `{% trans %}`); there is no JS translation catalog.
- Data for JS goes through `json_script` or `data-*` attributes; endpoints are rendered with `{% url %}`, never hard-coded in JS.
- `static/js/app.js` (every page): `App.brl`, `App.post` (CSRF), `<form data-confirm>` and `<button data-post-url [data-confirm]>` (POST, reload on success). Page scripts live next to their app (`reports/static/js/`, `registers/static/js/`).

## Common Development Commands

### Development Server
```bash
# Activate virtual environment first
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

### Database Operations
```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Access database directly
sqlite3 db.sqlite3
```

### Custom Management Commands
```bash
# Import a standard CSV (date,description,amount[,category,type,payment_method])
python manage.py import_csv path/to/file.csv [--user USERNAME] [--preview]

# Export all expenses to CSV
python manage.py export_expenses --output expenses.csv

# Generate this year's expenses of every user's active recurring expenses
python manage.py recurrence_payment [--month N]
```

### CSV Import
Expected format:
```csv
date,description,amount,category,type,payment_method
2025-09-02,Uber Uber *Trip Help.U,8.96,Uber,expense,Crédito - Nubank
```
A row is an expense or an income by its `type` column; without it, by the amount's sign (negative = expense). Amounts are stored as absolute values. See `registers/csv/importer.py`.

## Database Configuration

Uses SQLite for development and PostgreSQL for production via DATABASE_URL environment variable:
- SQLite: Local development with connection pooling (60s max age)
- PostgreSQL: Production with SSL and optimized connection settings

## Performance Notes
- Querysets that feed templates use `select_related` for the foreign keys they render.
- Dashboard aggregations are single grouped queries (`in_billing_year(...).values(...).annotate(Sum)`).
- Admin list views use `select_related` in `get_queryset`.

## Environment Configuration

### Environment Variables
- `SECRET_KEY`: Django secret key
- `DEBUG`: Enable/disable debug mode
- `ALLOWED_HOSTS`: Comma-separated allowed hosts
- `DATABASE_URL`: PostgreSQL connection string for production

### Settings Features
- WhiteNoise for static files in production
- Custom timezone: America/Sao_Paulo
- Session optimization with cached database sessions
- SQL query logging enabled for performance monitoring

## URL Structure

### Main Routes
- `/`: Expense reports dashboard
- `/admin/`: Django admin interface
- `/register/expense`: Add new expenses
- `/register/income`: Add new income
- `/register/csv-import`: Bulk import from CSV files

### JSON Endpoints
- `/daily-spending-data/`: daily spending chart data (`?days=&category_id=`)
- `/payment-notifications/`: the bell pop-up (counts + HTML)
- `/recurring-expense/<id>/payment/`: save a recurring occurrence's paid state
- `/register/categories/search/` and `/register/categories/create/`: category autocomplete
- `/register/{expense,income}/<id>/delete/`, `/register/quick-fill-presets/<id>/delete/`, `/recurring-expense/<id>/{delete,toggle}/`
- `/mcp/<MCP_TOKEN>/`: MCP server for registering expenses/incomes from Claude

## Key Development Patterns

### Where code goes
- A rule about one model (billing month, recurring occurrence, installment plan) → a method/queryset on the model.
- A dashboard number or chart → a function in `reports/services/<feature>.py` that takes `user` and returns numbers.
- A page → a view module next to its feature; the template formats.

### Query Optimization
```python
# note: 'reccurring_expense' has a typo (double 'c') that persists in migrations
queryset.select_related('category', 'payment_method', 'reccurring_expense')
```
**Note**: The field `reccurring_expense` has a typo (double 'c') that persists in migrations and cannot be easily renamed. Its reverse accessor on RecurringExpense is `recurring_expenses`.

## Testing Commands

`.env` points `DATABASE_URL` at the production database, so always clear it when running tests (SQLite):

```bash
# Run all tests (includes Playwright UI tests in registers/tests/ui/)
DATABASE_URL= python manage.py test

# One app / module / class / method (apps with tests: registers, reports, export, utils)
DATABASE_URL= python manage.py test reports
DATABASE_URL= python manage.py test registers.tests.test_csv_import
DATABASE_URL= python manage.py test reports.tests.test_billing_month
```

Shared test helpers live in `utils/tests/`: `clock.today_is(date)` / `clock.at(datetime)` freeze Django's clock, `html.page(response)` / `links_to` / `with_id` read a rendered page.

## Database Migration Between SQLite and PostgreSQL

### Migrating from PostgreSQL to SQLite

When you need to switch from PostgreSQL back to SQLite for local development:

```bash
# 1. Backup data from PostgreSQL (while DATABASE_URL is still active)
python manage.py dumpdata --indent=2 > db_backup.json

# 2. Remove/comment DATABASE_URL in .env file
# DATABASE_URL=postgresql://...

# 3. Remove existing SQLite database and create new one
rm -f db.sqlite3
python manage.py migrate

# 4. Import data to SQLite
python manage.py loaddata db_backup.json

# 5. Test the application
python manage.py runserver
```

### Migrating from SQLite to PostgreSQL

When you need to switch from SQLite to PostgreSQL for production:

```bash
# 1. Backup data from SQLite
python manage.py dumpdata --indent=2 > db_backup.json

# 2. Add DATABASE_URL to .env file
DATABASE_URL=postgresql://user:password@host:port/database

# 3. Run migrations on PostgreSQL
python manage.py migrate

# 4. Import data to PostgreSQL
python manage.py loaddata db_backup.json

# 5. Test the application
python manage.py runserver
```

### Important Notes for Database Migration

- **Backup First**: Always create a backup with `dumpdata` before switching databases
- **Environment Variables**: The application automatically uses PostgreSQL when `DATABASE_URL` is set, otherwise defaults to SQLite
- **Data Preservation**: The `dumpdata`/`loaddata` process preserves all relationships and foreign keys
- **Performance**: Both databases maintain the same performance optimizations implemented in the codebase
- **File Location**: Backup files are created in the project root directory

### Troubleshooting Database Migration

If you encounter issues during migration:

```bash
# Check if backup file was created successfully
ls -la db_backup.json

# Verify database connection
python manage.py dbshell

# Check migration status
python manage.py showmigrations

# If needed, reset migrations (use with caution)
python manage.py migrate --fake-initial
```

## Static Files

Static files live in `static/` (site-wide) and each app's `static/` folder, and are served via WhiteNoise in production. Run `python manage.py collectstatic` before deployment.