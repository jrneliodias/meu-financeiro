"""Monthly expense export (page + CSV download)."""
import csv
import io
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from registers.models import Category, Expense, Installment, PaymentMethod, RecurringExpense


class ExpenseExportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exporter', password='x')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='Casa', type='expense')
        self.card = PaymentMethod.objects.create(name='Card', start_billing_day=3)

    def spend(self, description, amount='12.50', day=date(2026, 3, 2), user=None, **links):
        return Expense.objects.create(user=user or self.user, description=description, amount=Decimal(amount),
                                      date=day, category=self.category, payment_method=self.card, **links)

    def download(self, **params):
        with translation.override('pt-br'):
            response = self.client.get(reverse('expense_export'), {'month': 3, 'year': 2026, 'download': 1, **params})
        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
        return response, {row[2]: row for row in rows[1:]}

    def test_csv_lists_the_calendar_month_of_the_logged_user(self):
        self.spend('March 2nd')  # in February's bill (start day 3), but in March's calendar month
        self.spend('Other user', user=User.objects.create_user(username='other'))
        self.spend('April', day=date(2026, 4, 1))
        response, rows = self.download()
        self.assertEqual(list(rows), ['March 2nd'])
        self.assertIn('filename="despesas-2026-03.csv"', response['Content-Disposition'])

    def test_kind_column_and_installment_wins_over_recurring(self):
        plan = Installment.objects.create(user=self.user, description='TV', total_amount=Decimal('100'),
                                          total_installments=1, start_date=date(2026, 3, 2))
        schedule = RecurringExpense.objects.create(user=self.user, description='Gym', total_amount=Decimal('50'),
                                                   start_date=date(2026, 1, 2))
        self.spend('Installment', installment_plan=plan)
        self.spend('Recurring', reccurring_expense=schedule)
        self.spend('Both', installment_plan=plan, reccurring_expense=schedule)
        self.spend('Single')
        _, rows = self.download()
        self.assertEqual({name: row[6] for name, row in rows.items()},
                         {'Installment': 'Parcela', 'Recurring': 'Recorrente', 'Both': 'Parcela', 'Single': 'Avulsa'})

    def test_decimal_separator(self):
        self.spend('Lunch')
        self.assertEqual(self.download(decimal_sep=',')[1]['Lunch'][3], '12,50')
        self.assertEqual(self.download(decimal_sep=';')[1]['Lunch'][3], '12.50')

    def test_invalid_month_is_rejected(self):
        self.assertEqual(self.client.get(reverse('expense_export'), {'month': 13, 'year': 2026}).status_code, 400)
