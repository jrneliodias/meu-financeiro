# Generated for performance optimization
from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('registers', '0007_recurringexpense_generate_debit_and_more'),
    ]
    
    operations = [
        # Composite index for Expense(payment_method, date) - Most important for billing calculations
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS registers_expense_payment_method_date_idx ON registers_expense(payment_method_id, date);",
            reverse_sql="DROP INDEX IF EXISTS registers_expense_payment_method_date_idx;"
        ),
        
        # Composite index for Expense(category, date) - Important for category filtering
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS registers_expense_category_date_idx ON registers_expense(category_id, date);",
            reverse_sql="DROP INDEX IF EXISTS registers_expense_category_date_idx;"
        ),
        
        # Composite index for Expense(date, payment_method) - Alternative order for date-first queries
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS registers_expense_date_payment_method_idx ON registers_expense(date, payment_method_id);",
            reverse_sql="DROP INDEX IF EXISTS registers_expense_date_payment_method_idx;"
        ),
        
        # Index for Expense(date) - Covers year/month filtering efficiently
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS registers_expense_date_idx ON registers_expense(date);",
            reverse_sql="DROP INDEX IF EXISTS registers_expense_date_idx;"
        ),
        
        # Index for Income(date) - For income aggregations
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS registers_income_date_idx ON registers_income(date);",
            reverse_sql="DROP INDEX IF EXISTS registers_income_date_idx;"
        ),
        
        # Composite index for Expense(user, date) - Multi-tenant support
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS registers_expense_user_date_idx ON registers_expense(user_id, date);",
            reverse_sql="DROP INDEX IF EXISTS registers_expense_user_date_idx;"
        ),
        
        # Composite index for Income(user, date) - Multi-tenant support
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS registers_income_user_date_idx ON registers_income(user_id, date);",
            reverse_sql="DROP INDEX IF EXISTS registers_income_user_date_idx;"
        ),
    ]
