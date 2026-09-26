"""
Tests for the fixed-expense payment status feature: repository, service,
and view/endpoint behavior for marking recurring-expense occurrences as
paid/pending.
"""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, Expense, PaymentMethod, RecurringExpense
from reports.services.recurring_expense_service import RecurringExpenseService


class ProcessRecurringExpensesPaymentStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.recurring_expense = RecurringExpense.objects.create(
            user=self.user,
            description='Netflix',
            total_amount=50,
            start_date=date(2026, 1, 5),
            category=self.category,
            payment_method=self.payment_method,
        )
        self.service = RecurringExpenseService()

    def test_generated_expense_is_not_paid(self):
        result = self.service.process_recurring_expenses_for_month(self.user, 9, 2026)

        self.assertEqual(result['created_count'], 1)
        expense = Expense.objects.get(reccurring_expense=self.recurring_expense)
        self.assertFalse(expense.is_paid)
        self.assertIsNone(expense.paid_at)
