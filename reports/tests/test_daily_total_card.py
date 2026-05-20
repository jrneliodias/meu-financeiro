from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from registers.models import Expense, Category, PaymentMethod
from reports.repository.expense_repository import ExpenseRepository


class GetTotalByDateTest(TestCase):
    def setUp(self):
        self.repo = ExpenseRepository()
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.category = Category.objects.create(name='Alimentação', type='expense')
        self.payment = PaymentMethod.objects.create(name='Débito', start_billing_day=1)
        self.today = date(2026, 5, 20)

    def test_returns_sum_of_expenses_for_date(self):
        Expense.objects.create(
            description='Almoço', amount=Decimal('35.00'),
            date=self.today, category=self.category, payment_method=self.payment,
            user=self.user
        )
        Expense.objects.create(
            description='Café', amount=Decimal('15.50'),
            date=self.today, category=self.category, payment_method=self.payment,
            user=self.user
        )
        total = self.repo.get_total_by_date(self.today)
        self.assertEqual(total, Decimal('50.50'))

    def test_returns_zero_when_no_expenses(self):
        total = self.repo.get_total_by_date(self.today)
        self.assertEqual(total, Decimal('0.00'))

    def test_ignores_expenses_from_other_dates(self):
        other_day = date(2026, 5, 19)
        Expense.objects.create(
            description='Ontem', amount=Decimal('100.00'),
            date=other_day, category=self.category, payment_method=self.payment,
            user=self.user
        )
        total = self.repo.get_total_by_date(self.today)
        self.assertEqual(total, Decimal('0.00'))
