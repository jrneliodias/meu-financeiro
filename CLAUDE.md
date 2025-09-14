# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based personal finance management application called "Meu Financeiro" that helps users track expenses, income, investments, and generate financial reports.

## Architecture

### Core Django Apps
- **finance**: Main Django project settings and URL routing
- **registers**: Handles data entry for expenses, incomes, installments, and CSV imports
- **reports**: Generates financial reports and analytics with performance-optimized views
- **utils**: Shared utilities like date handling functions

### Key Models (registers/models.py)
- **Expense**: Individual expense records with category, payment method, and installment/recurring expense links
- **Income**: Income records with categories
- **Category**: Expense/income categorization with type field (expense/income)
- **PaymentMethod**: Credit cards, bank accounts with billing cycles
- **Installment**: Multi-payment purchase plans that generate individual expenses
- **RecurringExpense**: Monthly recurring expenses that auto-generate expense records
- **Investment**: Investment tracking

### Service Layer Architecture
The codebase uses a service layer pattern with clear separation of concerns:

#### registers/services
- **ExpenseService**: Expense creation, editing, and business logic
- **IncomeService**: Income management and validation
- **InstallmentService**: Multi-payment purchase plan handling
- **CSVImportService**: Bulk data import with validation and error handling

#### reports/services
- **ExpenseService**: Report-specific expense calculations
- **BalanceService**: Financial balance calculations
- **ExpenseCalculator**: Monthly and period-based expense aggregations
- **CategoryCalculator**: Category-based expense analysis
- **BillingPeriodCalculator**: Credit card billing cycle calculations
- **DailyExpenseCalculator**: Daily spending trend analysis

#### reports/repository
Data access layer with performance-optimized queries:
- **ExpenseRepository**: Complex expense queries with select_related optimizations
- **CategoryRepository**: Category-based data aggregation
- **PaymentMethodRepository**: Payment method analysis queries
- **IncomeRepository**: Income data access with performance optimizations

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

### Performance Testing
```bash
# Measure query performance (custom command)
python manage.py measure_performance --iterations=5

# Run with SQL query explanation
python manage.py measure_performance --explain
```

### Custom Management Commands
```bash
# Import CSV data
python manage.py import_csv path/to/file.csv

# Export expenses to CSV
python manage.py export_expenses

# Process recurring payments (monthly automation)
python manage.py recurrence_payment

# Import legacy data
python manage.py import_data

# Run expense service operations
python manage.py run_expense_service
```

### CSV Import
The application supports CSV import with the following expected format:
```csv
date,description,amount,category,type,payment_method
2025-09-02,Uber Uber *Trip Help.U,8.96,Uber,expense,Crédito - Nubank
```

## Database Configuration

Uses SQLite for development and PostgreSQL for production via DATABASE_URL environment variable:
- SQLite: Local development with connection pooling (60s max age)
- PostgreSQL: Production with SSL and optimized connection settings

## Performance Optimizations

The codebase has been heavily optimized for performance:

### Query Optimization
- All admin views use `select_related()` to eliminate N+1 queries
- Report views use consolidated queries instead of multiple database hits
- Repository pattern abstracts complex queries
- Cache configuration using Django's local memory cache (5-minute timeout)

### Key Optimization Areas
- **Admin Interface**: Uses select_related for all foreign key relationships
- **Expense Reports**: Single aggregated queries replace multiple individual queries
- **Monthly Reports**: Optimized data retrieval reduces 50+ queries to 3-5 queries
- **Template Rendering**: Pre-aggregated data prevents N+1 queries in templates

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

### API Endpoints
- `/daily-spending-data/`: AJAX endpoint for spending trends
- `/expense-details/`: AJAX endpoint for detailed expense information

## Key Development Patterns

### Service Layer Usage
Always use services for business logic instead of putting logic in views:
```python
# Good
expense_service = ExpenseService()
expense = expense_service.create_single_expense(user, expense_data)

# Avoid putting business logic directly in views
```

### Query Optimization
Always use select_related/prefetch_related for foreign key access:
```python
# Good
queryset.select_related('category', 'payment_method', 'reccurring_expense')

# Bad - causes N+1 queries
queryset  # then accessing .category in templates
```

### Repository Pattern
Use repository classes for complex queries:
```python
expense_repository = ExpenseRepository()
expenses = expense_repository.get_optimized_monthly_expenses(month)
```

## Testing Commands

Run Django's built-in tests:
```bash
python manage.py test

# Test specific app
python manage.py test registers
python manage.py test reports
```

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

Static files are located in `registers/static/css/` and served via WhiteNoise in production. Run `python manage.py collectstatic` before deployment.