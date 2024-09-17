# Generated by Django 5.1.1 on 2024-09-17 20:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registers', '0005_recurringexpense_expense_reccurring_expense'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethod',
            name='start_billing_day',
            field=models.IntegerField(default=1, help_text='Day of the month when billing starts'),
            preserve_default=False,
        ),
    ]
