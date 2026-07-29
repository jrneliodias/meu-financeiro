"""
Tests for the "Recurring expense" checkbox on the expense registration form.
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.forms import ExpenseForm
from registers.models import Category, Expense, PaymentMethod, RecurringExpense
from registers.services.expense_service import ExpenseService


class ExpenseServiceRecurringLinkTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.service = ExpenseService()

    def test_create_single_expense_links_recurring_expense(self):
        recurring_expense = RecurringExpense.objects.create(
            user=self.user,
            description='Gym',
            total_amount=100,
            start_date=date(2026, 7, 1),
            category=self.category,
            payment_method=self.payment_method,
        )

        expense = self.service.create_single_expense(
            self.user,
            {
                'description': 'Gym',
                'amount': 100,
                'date': date(2026, 7, 1),
                'category': self.category,
                'payment_method': self.payment_method,
            },
            recurring_expense=recurring_expense,
        )

        self.assertEqual(expense.reccurring_expense, recurring_expense)

    def test_create_single_expense_without_recurring_expense(self):
        expense = self.service.create_single_expense(
            self.user,
            {
                'description': 'Coffee',
                'amount': 10,
                'date': date(2026, 7, 1),
                'category': self.category,
                'payment_method': self.payment_method,
            },
        )

        self.assertIsNone(expense.reccurring_expense)


class ExpenseFormRecurringValidationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)

    def _form_data(self, **overrides):
        data = {
            'description': 'Gym',
            'amount': '100',
            'installments': 1,
            'date': '2026-07-01',
            'category': self.category.id,
            'payment_method': self.payment_method.id,
        }
        data.update(overrides)
        return data

    def test_recurring_with_installments_is_invalid(self):
        form = ExpenseForm(
            data=self._form_data(is_recurring=True, installments=3),
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_recurring_without_installments_is_valid(self):
        form = ExpenseForm(
            data=self._form_data(is_recurring=True, installments=1),
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_defaults_to_not_recurring(self):
        form = ExpenseForm(data=self._form_data(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data['is_recurring'])


class RegisterExpenseViewRecurringTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)

    def test_checking_recurring_creates_recurring_expense_and_links_it(self):
        response = self.client.post(reverse('register_expense'), {
            'description': 'Gym',
            'amount': '100',
            'installments': 1,
            'date': '2026-07-01',
            'category': self.category.id,
            'payment_method': self.payment_method.id,
            'is_recurring': 'on',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(RecurringExpense.objects.count(), 1)
        expense = Expense.objects.get(description='Gym')
        recurring_expense = RecurringExpense.objects.get()
        self.assertEqual(expense.reccurring_expense, recurring_expense)
        self.assertEqual(recurring_expense.total_amount, 100)

    def test_unchecked_recurring_does_not_create_recurring_expense(self):
        response = self.client.post(reverse('register_expense'), {
            'description': 'Coffee',
            'amount': '10',
            'installments': 1,
            'date': '2026-07-01',
            'category': self.category.id,
            'payment_method': self.payment_method.id,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(RecurringExpense.objects.count(), 0)
        expense = Expense.objects.get(description='Coffee')
        self.assertIsNone(expense.reccurring_expense)
