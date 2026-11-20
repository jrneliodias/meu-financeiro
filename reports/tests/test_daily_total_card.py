from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate

from registers.models import Category, Expense, PaymentMethod
from reports.services.summary import spent_on
from utils.tests.html import links_to, page


class SpentTodayTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.category = Category.objects.create(name='Alimentação', type='expense')
        self.payment = PaymentMethod.objects.create(name='Débito', start_billing_day=1)

    def _expense(self, amount, day, user=None):
        Expense.objects.create(user=user or self.user, description='x', amount=Decimal(amount), date=day,
                               category=self.category, payment_method=self.payment)

    def test_sums_the_day_expenses(self):
        self._expense('35.00', date(2026, 5, 20))
        self._expense('15.50', date(2026, 5, 20))
        self.assertEqual(spent_on(self.user, date(2026, 5, 20)), Decimal('50.50'))

    def test_zero_when_no_expenses(self):
        self.assertEqual(spent_on(self.user, date(2026, 5, 20)), Decimal('0'))

    def test_ignores_other_days_and_other_users(self):
        self._expense('100.00', date(2026, 5, 19))
        self._expense('70.00', date(2026, 5, 20), user=User.objects.create_user(username='other'))
        self.assertEqual(spent_on(self.user, date(2026, 5, 20)), Decimal('0'))

    def test_resumo_card_shows_today_total_and_links_to_today_list(self):
        today = localdate()
        self._expense('42.00', today)
        self._expense('99.00', today - timedelta(days=1))
        self.client.force_login(self.user)
        elements = page(self.client.get(reverse('expense_report')))
        [card] = links_to(elements, reverse('expense_list_page'), date=today.isoformat())
        self.assertIn('R$ 42,00', card['text'])
