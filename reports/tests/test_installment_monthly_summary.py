from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, Installment, PaymentMethod
from reports.services.budget import monthly_budget
from utils.tests.html import links_to, page


class MonthlyInstallmentsTest(TestCase):
    """The bill's installment total ("Parcelas do mês")."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.category = Category.objects.create(name='Electronics', type='expense')
        self.card = PaymentMethod.objects.create(name='Credit Card', start_billing_day=10)
        self.installment = Installment.objects.create(
            user=self.user, description='iPhone 15', total_amount=Decimal('3000.00'), total_installments=12,
            start_date=date(2026, 1, 1), category=self.category, payment_method=self.card)

    def _expense(self, description, amount, day, plan=None, user=None):
        Expense.objects.create(user=user or self.user, description=description, amount=Decimal(amount), date=day,
                               category=self.category, payment_method=self.card, installment_plan=plan)

    def june_installments(self):
        return monthly_budget(self.user, month=6, year=2026).total_installments

    def test_sums_only_installment_expenses_of_the_bill(self):
        self._expense('iPhone 15 - 1/12', '250.00', date(2026, 6, 10), self.installment)
        self._expense('iPhone 15 - 2/12', '250.00', date(2026, 6, 15), self.installment)
        self._expense('Almoço', '50.00', date(2026, 6, 10))  # not an installment
        self.assertEqual(self.june_installments(), Decimal('500.00'))

    def test_ignores_other_months(self):
        self._expense('iPhone 15 - 1/12', '250.00', date(2026, 5, 10), self.installment)
        self.assertEqual(self.june_installments(), Decimal('0'))

    def test_ignores_other_users(self):
        other = User.objects.create_user(username='other', password='pass')
        tv = Installment.objects.create(user=other, description='TV', total_amount=Decimal('1200.00'),
                                        total_installments=6, start_date=date(2026, 1, 1))
        self._expense('TV - 1/6', '200.00', date(2026, 6, 10), tv, user=other)
        self.assertEqual(self.june_installments(), Decimal('0'))

    def test_resumo_card_shows_the_total_in_reais_and_links_to_the_list(self):
        self.client.force_login(self.user)

        def card_text():
            response = self.client.get(reverse('expense_report'), {'month': 6, 'year': 2026})
            [card] = links_to(page(response), reverse('expense_list_page'), installments='1', month='6', year='2026')
            return card['text']

        self.assertIn('R$\xa00,00', card_text())
        self._expense('iPhone 15 - 1/12', '1250.00', date(2026, 6, 10), self.installment)
        self.assertIn('R$\xa01.250,00', card_text())
