"""Every edit, delete and toggle answers 404 for another user's record and changes nothing."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import (
    Category, CategoryBudgetEstimate, Expense, Income, PaymentMethod, QuickFillPreset, RecurringExpense,
)


class OwnershipTest(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username='owner')
        self.client.force_login(User.objects.create_user(username='intruder', password='x'))
        food = Category.objects.create(name='Food', type='expense')
        card = PaymentMethod.objects.create(name='Card', start_billing_day=1)
        self.schedule = RecurringExpense.objects.create(user=owner, description='Gym', total_amount=Decimal('50'),
                                                        start_date=date(2026, 1, 5), category=food, payment_method=card)
        self.expense = Expense.objects.create(user=owner, description='Lunch', amount=Decimal('30'),
                                              date=date(2026, 3, 1), category=food, payment_method=card)
        self.occurrence = Expense.objects.create(user=owner, description='Gym', amount=Decimal('50'), is_paid=False,
                                                 date=date(2026, 3, 5), reccurring_expense=self.schedule)
        self.income = Income.objects.create(user=owner, description='Salary', amount=Decimal('900'), date=date(2026, 3, 5))
        self.preset = QuickFillPreset.objects.create(user=owner, name='Uber', description='Uber')
        self.estimate = CategoryBudgetEstimate.objects.create(user=owner, category=food, amount=Decimal('100'),
                                                              month=3, year=2026)

    def snapshot(self):
        return (list(Expense.objects.values().order_by('pk')), list(Income.objects.values()),
                list(RecurringExpense.objects.values()), list(QuickFillPreset.objects.values()),
                list(CategoryBudgetEstimate.objects.values()))

    def test_other_users_records_are_not_found(self):
        before = self.snapshot()
        pages = [('expense_update', self.expense), ('recurring_expense_update', self.schedule),
                 ('recurring_expense_expenses', self.schedule), ('budget_estimate_update', self.estimate),
                 ('quick_fill_preset_edit', self.preset)]
        for name, record in pages:
            for method in ('get', 'post'):
                with self.subTest(name=name, method=method):
                    response = getattr(self.client, method)(reverse(name, args=[record.pk]))
                    self.assertEqual(response.status_code, 404)
        json_posts = [('delete_expense', self.expense), ('delete_income', self.income),
                      ('quick_fill_preset_delete', self.preset), ('recurring_expense_delete', self.schedule),
                      ('recurring_expense_toggle', self.schedule)]
        for name, record in json_posts:
            with self.subTest(name=name):
                response = self.client.post(reverse(name, args=[record.pk]))
                self.assertEqual(response.status_code, 404)
                self.assertIn('error', response.json())
        with self.subTest(name='recurring_expense_set_paid'):
            response = self.client.post(reverse('recurring_expense_set_paid', args=[self.occurrence.pk]),
                                        {'is_paid': True}, content_type='application/json')
            self.assertEqual(response.status_code, 404)
            self.assertIn('error', response.json())
        with self.subTest(name='budget_estimate_delete'):
            self.assertEqual(self.client.post(reverse('budget_estimate_delete', args=[self.estimate.pk])).status_code, 404)
        self.assertEqual(self.snapshot(), before)
