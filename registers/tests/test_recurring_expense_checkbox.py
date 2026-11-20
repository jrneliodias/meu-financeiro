"""
Tests for the "Recurring expense" checkbox on the expense registration page.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod, RecurringExpense


class RegisterExpenseViewRecurringTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)

    def post(self, **overrides):
        data = {
            'description': 'Gym',
            'amount': '100',
            'installments': 1,
            'date': '2026-07-01',
            'category': self.category.id,
            'payment_method': self.payment_method.id,
        }
        data.update(overrides)
        return self.client.post(reverse('register_expense'), data)

    def test_checking_recurring_creates_recurring_expense_and_links_it(self):
        response = self.post(is_recurring='on')

        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(description='Gym')
        recurring_expense = RecurringExpense.objects.get()
        self.assertEqual(expense.reccurring_expense, recurring_expense)
        self.assertEqual(recurring_expense.user, self.user)
        self.assertEqual(recurring_expense.total_amount, 100)

    def test_unchecked_recurring_does_not_create_recurring_expense(self):
        response = self.post(description='Coffee', amount='10')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(RecurringExpense.objects.count(), 0)
        self.assertIsNone(Expense.objects.get(description='Coffee').reccurring_expense)

    def test_recurring_with_installments_is_rejected(self):
        response = self.post(is_recurring='on', installments=3)

        self.assertEqual(response.status_code, 200)  # back on the form, not redirected
        self.assertFalse(Expense.objects.exists())
        self.assertFalse(RecurringExpense.objects.exists())
