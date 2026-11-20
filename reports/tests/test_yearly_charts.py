from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import translation

from registers.models import Category, Expense, Income, PaymentMethod
from reports.services.summary import yearly_charts

MARCH, DECEMBER = 2, 11  # indexes in the 12-month series


class YearlyChartsTest(TestCase):
    """Resumo's two charts: spending per payment method per bill, and spending vs income per month."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.credit_card = PaymentMethod.objects.create(name='Credit Card', start_billing_day=15)
        self.debit_card = PaymentMethod.objects.create(name='Debit Card', start_billing_day=1)
        self.category = Category.objects.create(name='Test Category', type='expense')

    def _expense(self, day, amount, method):
        Expense.objects.create(user=self.user, description='x', amount=Decimal(amount), date=day,
                               category=self.category, payment_method=method)

    def test_december_bill_includes_next_january_expenses(self):
        # the December 2024 bill runs Dec 15 2024 - Jan 14 2025 and captures both expenses
        self._expense(date(2024, 12, 20), '100.00', self.credit_card)
        self._expense(date(2025, 1, 10), '150.00', self.credit_card)
        datasets = yearly_charts(self.user, 2024)['payment_methods']['datasets']
        [credit] = [d['data'] for d in datasets if d['label'] == 'Credit Card']
        self.assertEqual(credit[DECEMBER], 250.0)

    def test_total_expenses_per_month(self):
        for day in range(1, 4):
            self._expense(date(2024, 3, day), '100.00', self.debit_card)
        expenses, _income = yearly_charts(self.user, 2024)['expense_income']['datasets']
        self.assertEqual(expenses['data'][MARCH], 300.0)

    def test_income_per_month(self):
        Income.objects.create(user=self.user, description='March Salary', amount=Decimal('5000.00'),
                              date=date(2024, 3, 5))
        _expenses, income = yearly_charts(self.user, 2024)['expense_income']['datasets']
        self.assertEqual(income['data'][MARCH], 5000.0)

    def test_investment_payment_method_is_left_out_of_spending(self):
        investment = PaymentMethod.objects.create(name='Investimento', start_billing_day=1)
        self._expense(date(2026, 3, 5), '500.00', investment)
        self._expense(date(2026, 3, 6), '40.00', self.debit_card)
        charts = yearly_charts(self.user, 2026)
        self.assertNotIn('Investimento', [ds['label'] for ds in charts['payment_methods']['datasets']])
        self.assertEqual(charts['expense_income']['datasets'][0]['data'][MARCH], 40.0)

    def test_expenses_without_payment_method_have_their_own_series(self):
        Expense.objects.create(user=self.user, description='cash', amount=Decimal('12'), date=date(2026, 3, 5),
                               category=self.category)
        with translation.override('en'):
            labels = [ds['label'] for ds in yearly_charts(self.user, 2026)['payment_methods']['datasets']]
        self.assertEqual(labels, ['No Payment Method'])
