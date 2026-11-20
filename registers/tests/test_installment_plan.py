"""Registering an expense in N installments creates a plan and one expense per month."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, Installment, PaymentMethod


class InstallmentPlanTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='x')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='Casa', type='expense')
        self.card = PaymentMethod.objects.create(name='Card', start_billing_day=3)

    def register(self, installments):
        return self.client.post(reverse('register_expense'), {
            'description': 'TV', 'amount': '100', 'installments': installments, 'date': '2026-01-31',
            'category': self.category.pk, 'payment_method': self.card.pk,
        })

    def test_creates_one_expense_per_month_with_numbered_descriptions(self):
        self.register('3')
        expenses = list(Expense.objects.order_by('date'))
        self.assertEqual([e.description for e in expenses], ['TV - 1/3', 'TV - 2/3', 'TV - 3/3'])
        self.assertEqual([e.date for e in expenses], [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)])
        plan = Installment.objects.get()
        self.assertEqual((plan.total_amount, plan.total_installments, plan.user), (Decimal('100'), 3, self.user))
        self.assertTrue(all(e.installment_plan == plan and e.user == self.user for e in expenses))

    def test_installments_split_the_total(self):
        # how the leftover fraction is placed is an open decision; only the split itself is pinned
        self.register('3')
        amounts = [e.amount for e in Expense.objects.all()]
        self.assertTrue(all(abs(amount - Decimal('100') / 3) < Decimal('0.01') for amount in amounts))
        self.assertLess(abs(sum(amounts) - Decimal('100')), Decimal('0.01'))

    def test_single_installment_creates_a_plain_expense(self):
        self.register('1')
        self.assertEqual(Installment.objects.count(), 0)
        self.assertIsNone(Expense.objects.get().installment_plan)
