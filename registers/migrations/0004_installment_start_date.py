# Generated by Django 5.1.1 on 2024-09-08 18:04

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registers', '0003_installment_expense_installment_plan'),
    ]

    operations = [
        migrations.AddField(
            model_name='installment',
            name='start_date',
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
