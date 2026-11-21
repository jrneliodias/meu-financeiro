"""Resumo's balance: all income minus all expenses up to the end of the current month."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Expense, Income
from reports.services.summary import global_balance
from utils.tests.clock import today_is


class GlobalBalanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='saver', password='x')
        Income.objects.create(user=self.user, description='Salary', amount=Decimal('1000'), date=date(2026, 3, 5))
        # after 'today' (Mar 15) but still this month: counts
        Expense.objects.create(user=self.user, description='Rent', amount=Decimal('616.999'), date=date(2026, 3, 20))
        Income.objects.create(user=self.user, description='Next', amount=Decimal('999'), date=date(2026, 4, 1))

    def test_balance_is_income_minus_expenses_up_to_the_end_of_this_month(self):
        self.client.force_login(self.user)
        with today_is(date(2026, 3, 15)):
            self.assertEqual(global_balance(self.user), Decimal('383.001'))
            self.assertContains(self.client.get(reverse('expense_report')), 'R$\xa0383,00')

    def test_balance_ignores_other_users(self):
        other = User.objects.create_user(username='other')
        Income.objects.create(user=other, description='x', amount=Decimal('5000'), date=date(2026, 3, 1))
        Expense.objects.create(user=other, description='x', amount=Decimal('70'), date=date(2026, 3, 1))
        with today_is(date(2026, 3, 15)):
            self.assertEqual(global_balance(self.user), Decimal('383.001'))
