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
