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


class ToggleExpensePaidTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='12345')
        self.other_user = User.objects.create_user(username='intruder', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.recurring_expense = RecurringExpense.objects.create(
            user=self.user,
            description='Netflix',
            total_amount=50,
            start_date=date(2026, 9, 5),
            category=self.category,
            payment_method=self.payment_method,
        )
        self.expense = Expense.objects.create(
            user=self.user,
            description='Netflix',
            amount=50,
            date=date(2026, 9, 5),
            category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=self.recurring_expense,
            is_paid=False,
        )
        self.service = RecurringExpenseService()

    def test_toggle_marks_expense_as_paid(self):
        updated = self.service.toggle_paid(self.expense.id, self.user)

        self.assertTrue(updated.is_paid)
        self.assertIsNotNone(updated.paid_at)

    def test_toggle_twice_marks_expense_as_pending_again(self):
        self.service.toggle_paid(self.expense.id, self.user)
        updated = self.service.toggle_paid(self.expense.id, self.user)

        self.assertFalse(updated.is_paid)
        self.assertIsNone(updated.paid_at)

    def test_cannot_toggle_another_users_expense(self):
        with self.assertRaises(Expense.DoesNotExist):
            self.service.toggle_paid(self.expense.id, self.other_user)

    def test_cannot_toggle_expense_without_recurring_link(self):
        manual_expense = Expense.objects.create(
            user=self.user,
            description='Coffee',
            amount=10,
            date=date(2026, 9, 6),
            category=self.category,
            payment_method=self.payment_method,
        )

        with self.assertRaises(Expense.DoesNotExist):
            self.service.toggle_paid(manual_expense.id, self.user)


class MonthExpensesWithStatusTest(TestCase):
    def setUp(self):
        from reports.repository.recurring_expense_repository import RecurringExpenseRepository
        self.user = User.objects.create_user(username='owner2', password='12345')
        self.other_user = User.objects.create_user(username='intruder2', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.repository = RecurringExpenseRepository()

        self.paid_recurring = RecurringExpense.objects.create(
            user=self.user, description='Netflix', total_amount=50,
            start_date=date(2026, 1, 5), category=self.category,
            payment_method=self.payment_method,
        )
        Expense.objects.create(
            user=self.user, description='Netflix', amount=50,
            date=date(2026, 9, 5), category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=self.paid_recurring, is_paid=True,
        )

        self.pending_recurring = RecurringExpense.objects.create(
            user=self.user, description='Internet', total_amount=100,
            start_date=date(2026, 1, 10), category=self.category,
            payment_method=self.payment_method,
        )
        Expense.objects.create(
            user=self.user, description='Internet', amount=100,
            date=date(2026, 9, 10), category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=self.pending_recurring, is_paid=False,
        )

        RecurringExpense.objects.create(
            user=self.user, description='Gym', total_amount=80,
            start_date=date(2026, 1, 15), category=self.category,
            payment_method=self.payment_method,
        )

        RecurringExpense.objects.create(
            user=self.user, description='Old Subscription', total_amount=20,
            start_date=date(2026, 1, 20), category=self.category,
            payment_method=self.payment_method, generate_debit=False,
        )

        RecurringExpense.objects.create(
            user=self.other_user, description='Other User Rent', total_amount=999,
            start_date=date(2026, 1, 1), category=self.category,
            payment_method=self.payment_method,
        )

    def test_returns_status_per_active_recurring_expense(self):
        results = self.repository.get_month_expenses_with_status(self.user, 9, 2026)

        statuses = {entry['recurring_expense'].description: entry['status'] for entry in results}
        self.assertEqual(statuses, {
            'Netflix': 'paid',
            'Internet': 'pending',
            'Gym': 'not_generated',
        })

    def test_excludes_inactive_and_other_users_recurring_expenses(self):
        results = self.repository.get_month_expenses_with_status(self.user, 9, 2026)

        descriptions = [entry['recurring_expense'].description for entry in results]
        self.assertNotIn('Old Subscription', descriptions)
        self.assertNotIn('Other User Rent', descriptions)

    def test_bounded_query_count(self):
        with self.assertNumQueries(2):
            self.repository.get_month_expenses_with_status(self.user, 9, 2026)


class FixedExpensesSummaryPaymentStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner3', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.service = RecurringExpenseService()

        recurring = RecurringExpense.objects.create(
            user=self.user, description='Netflix', total_amount=50,
            start_date=date(2026, 1, 5), category=self.category,
            payment_method=self.payment_method,
        )
        Expense.objects.create(
            user=self.user, description='Netflix', amount=50,
            date=date(2026, 9, 5), category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=recurring, is_paid=False,
        )

    def test_summary_includes_status_counts_for_month(self):
        summary = self.service.get_fixed_expenses_summary(self.user, 9, 2026)

        self.assertEqual(summary['pending_count'], 1)
        self.assertEqual(summary['paid_count'], 0)
        self.assertEqual(summary['not_generated_count'], 0)
        self.assertEqual(summary['count'], 1)
