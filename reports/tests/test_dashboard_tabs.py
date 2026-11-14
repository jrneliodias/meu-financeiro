from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod

TABS = ['expense_report', 'dashboard_spending', 'dashboard_categories',
        'dashboard_installments', 'dashboard_expenses']


class DashboardTabsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p')
        self.client.login(username='u', password='p')
        cat = Category.objects.create(name='Mercado', type='expense')
        pm = PaymentMethod.objects.create(name='Pix', start_billing_day=1)
        Expense.objects.create(user=self.user, description='Feira', amount=Decimal('42.00'),
                               date=date(2026, 10, 3), category=cat, payment_method=pm)

    def test_login_required(self):
        self.client.logout()
        for name in TABS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_every_tab_renders_and_marks_itself_active(self):
        for name in TABS:
            response = self.client.get(reverse(name), {'month': 10, 'year': 2026})
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'aria-current="page"')
            # o filtro de mês/ano é repassado aos links das outras abas
            self.assertContains(response, 'month=10&year=2026')

    def test_expenses_tab_lists_month_expenses(self):
        response = self.client.get(reverse('dashboard_expenses'), {'month': 10, 'year': 2026})
        self.assertContains(response, 'Feira')

    def test_home_does_not_compute_other_tabs(self):
        response = self.client.get(reverse('expense_report'), {'month': 10, 'year': 2026})
        for key in ('daily_spending_data', 'installments_progress', 'monthly_expenses_queryset',
                    'formatted_expenses_by_category'):
            self.assertNotIn(key, response.context)

    def test_notification_bell_once_on_every_tab(self):
        for name in TABS:
            response = self.client.get(reverse(name), {'month': 10, 'year': 2026})
            self.assertContains(response, 'id="payment-notifications-toggle"', count=1, msg_prefix=name)
