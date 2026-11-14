from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod, RecurringExpense


class RecurringProcessPageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='p', password='pw12345!')
        self.client.force_login(self.user)
        cat = Category.objects.create(name='Food', type='expense')
        method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.rec = RecurringExpense.objects.create(
            user=self.user, description='Unimed', total_amount=Decimal('100'),
            start_date=date(2024, 9, 25), category=cat, payment_method=method)
        self.url = reverse('recurring_expense_process')

    def test_get_shows_form(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'id="processMonth"')
        self.assertNotContains(response, 'id="process-result"')

    def test_creates_expense_and_is_idempotent(self):
        first = self.client.post(self.url, {'month': 11, 'year': 2026})
        self.assertEqual(first.status_code, 200)
        self.assertEqual((first.context['result']['created_count'], first.context['result']['skipped_count']), (1, 0))
        self.assertEqual(Expense.objects.filter(reccurring_expense=self.rec).count(), 1)
        again = self.client.post(self.url, {'month': 11, 'year': 2026})
        self.assertEqual((again.context['result']['created_count'], again.context['result']['skipped_count']), (0, 1))

    def test_invalid_month_year_returns_400(self):
        for data in ({'month': 13, 'year': 2026}, {'month': 'x', 'year': 2026}, {'year': 2026}):
            self.assertEqual(self.client.post(self.url, data).status_code, 400, data)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_list_page_links_to_process_page_without_modal(self):
        html = self.client.get(reverse('recurring_expense_list')).content.decode()
        self.assertIn(self.url, html)
        self.assertNotIn('processRecurringModal', html)
