from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod, RecurringExpense

AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


class ProcessRecurringAjaxTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='p', password='pw12345!')
        self.client.force_login(self.user)
        cat = Category.objects.create(name='Food', type='expense')
        self.method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.rec = RecurringExpense.objects.create(
            user=self.user, description='Unimed', total_amount=Decimal('100'),
            start_date=date(2024, 9, 25), category=cat, payment_method=self.method)
        self.url = reverse('process_recurring_expenses_ajax')

    def test_creates_expense_and_is_idempotent(self):
        r = self.client.post(self.url, {'month': 11, 'year': 2026}, **AJAX)
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertTrue(data['success'])
        self.assertEqual((data['created_count'], data['skipped_count']), (1, 0))
        self.assertEqual(Expense.objects.filter(reccurring_expense=self.rec).count(), 1)
        data = self.client.post(self.url, {'month': 11, 'year': 2026}, **AJAX).json()
        self.assertEqual((data['created_count'], data['skipped_count']), (0, 1))

    def test_list_page_renders_button_modal_and_script(self):
        html = self.client.get(reverse('recurring_expense_list')).content.decode()
        for needle in ('showProcessRecurringModal()', 'id="processRecurringModal"',
                       'id="processMonth"', 'recurring_expense_list.js'):
            self.assertIn(needle, html)
