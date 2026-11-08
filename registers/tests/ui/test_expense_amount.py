from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from registers.models import Category, Expense, PaymentMethod

from .base import UITestCase


class ExpenseAmountUITest(UITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='amt', password='pw12345!')
        category = Category.objects.create(name='Food', type='expense')
        method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.expense = Expense.objects.create(
            user=self.user, description='Coffee', amount=Decimal('10'),
            date=date(2026, 11, 8), category=category, payment_method=method)
        self.login(self.user)

    def test_edit_expense_accepts_four_decimals_and_rounds(self):
        self.page.goto(self.url(f'/expense/{self.expense.pk}/update/'))
        amount = self.page.locator('#id_amount')
        self.assertEqual(amount.get_attribute('step'), 'any')
        amount.fill('12.3456')
        self.page.click('button[type=submit]')
        self.page.wait_for_url(lambda u: '/update/' not in u)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.amount, Decimal('12.346'))
