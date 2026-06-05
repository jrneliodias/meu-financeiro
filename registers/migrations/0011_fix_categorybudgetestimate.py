from django.db import migrations


class Migration(migrations.Migration):
    """
    The previous 0010 migration file was replaced but the DB still has the old schema
    (estimation_method, manual_amount, is_active instead of amount, month, year).
    This migration fixes the actual DB without touching Django's migration state,
    which already reflects the correct model after 0010.
    """

    dependencies = [
        ('registers', '0010_categorybudgetestimate'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE registers_categorybudgetestimate
                            DROP COLUMN IF EXISTS estimation_method,
                            DROP COLUMN IF EXISTS manual_amount,
                            DROP COLUMN IF EXISTS is_active;

                        ALTER TABLE registers_categorybudgetestimate
                            ADD COLUMN IF NOT EXISTS amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
                            ADD COLUMN IF NOT EXISTS month INTEGER NOT NULL DEFAULT 1,
                            ADD COLUMN IF NOT EXISTS year INTEGER NOT NULL DEFAULT 2026;

                        ALTER TABLE registers_categorybudgetestimate
                            ALTER COLUMN amount DROP DEFAULT,
                            ALTER COLUMN month DROP DEFAULT,
                            ALTER COLUMN year DROP DEFAULT;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
