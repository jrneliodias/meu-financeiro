from django.db import migrations


def fix_postgres_unique_constraint(apps, schema_editor):
    """The original 0010 created UNIQUE(user_id, category_id). 0011 fixed the
    columns but left that constraint, blocking a second month per category.
    Swap it for UNIQUE(user_id, category_id, month, year), matching the model."""
    if schema_editor.connection.vendor != 'postgresql':
        return

    sql = """
        ALTER TABLE registers_categorybudgetestimate
            DROP CONSTRAINT IF EXISTS registers_categorybudget_user_id_category_id_4a788f6e_uniq;

        CREATE UNIQUE INDEX IF NOT EXISTS registers_categorybudgetestimate_user_cat_month_year_uniq
            ON registers_categorybudgetestimate (user_id, category_id, month, year);
    """
    for statement in schema_editor.connection.ops.prepare_sql_script(sql):
        schema_editor.execute(statement, params=None)


class Migration(migrations.Migration):

    dependencies = [
        ('registers', '0013_expense_is_paid_expense_paid_at'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(
                    fix_postgres_unique_constraint,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
        ),
    ]
