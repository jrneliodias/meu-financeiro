"""
Tests for the fixed-expense payment status feature (Expense.is_paid/paid_at).
"""
from datetime import date

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod, RecurringExpense


class ExpenseIsPaidDefaultTest(TestCase):
    def test_expense_registered_by_hand_is_paid(self):
        user = User.objects.create_user(username='testuser', password='12345')
        self.client.force_login(user)
        category = Category.objects.create(name='Food', type='expense')
        payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)

        self.client.post(reverse('register_expense'), {
            'description': 'Coffee', 'amount': '10', 'installments': 1, 'date': '2026-09-01',
            'category': category.id, 'payment_method': payment_method.id,
        })

        self.assertTrue(Expense.objects.get(description='Coffee').is_paid)


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
        call_command('recurrence_payment', month=9)

        expense = Expense.objects.get(reccurring_expense=self.recurring_expense)
        self.assertEqual(expense.date.month, 9)
        self.assertFalse(expense.is_paid)
        self.assertIsNone(expense.paid_at)
