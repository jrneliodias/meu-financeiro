"""
Tests for the fixed-expense payment status feature (Expense.is_paid/paid_at).
"""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, Expense, PaymentMethod


class ExpenseIsPaidDefaultTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)

    def test_manually_created_expense_defaults_to_paid(self):
        expense = Expense.objects.create(
            user=self.user,
            description='Coffee',
            amount=10,
            date=date(2026, 9, 1),
            category=self.category,
            payment_method=self.payment_method,
        )

        self.assertTrue(expense.is_paid)
        self.assertIsNone(expense.paid_at)


from django.core.management import call_command

from registers.models import RecurringExpense


class RecurrencePaymentCommandPaymentStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cmduser', password='12345')
        self.category = Category.objects.create(name='Subscriptions', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Card', start_billing_day=1)
        self.recurring_expense = RecurringExpense.objects.create(
            user=self.user,
            description='Netflix',
            total_amount=50,
            start_date=date(2026, 1, 1),
            category=self.category,
            payment_method=self.payment_method,
        )

    def test_generated_expense_is_not_paid(self):
        current_month = 9  # September for consistency
        call_command('recurrence_payment', month=current_month)

        expense = Expense.objects.get(reccurring_expense=self.recurring_expense)
        self.assertFalse(expense.is_paid)
        self.assertIsNone(expense.paid_at)
