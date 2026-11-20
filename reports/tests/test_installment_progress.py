"""Open installment plans (Parcelas tab): an expense dated up to the chosen month counts as paid."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, Installment, PaymentMethod
from reports.services.installments import open_installments


class InstallmentProgressTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='x')
        self.category = Category.objects.create(name='Casa', type='expense')
        self.card = PaymentMethod.objects.create(name='Card', start_billing_day=3)
        self.plan('TV', [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)], '33.333')

    def plan(self, description, days, amount, user=None):
        """A plan with its expenses written out, so these tests don't depend on how create_plan splits."""
        user = user or self.user
        plan = Installment.objects.create(
            user=user, description=description, total_amount=Decimal('100'), total_installments=len(days),
            start_date=days[0], category=self.category, payment_method=self.card)
        for day in days:
            Expense.objects.create(user=user, description=description, amount=Decimal(amount), date=day,
                                   category=self.category, payment_method=self.card, installment_plan=plan)

    def test_expenses_up_to_the_month_count_as_paid(self):
        summary = open_installments(self.user, 2026, 2)
        self.assertEqual(summary['count'], 1)
        tv = summary['installments'][0]
        self.assertEqual(tv.paid_installments, 2)
        self.assertEqual(tv.paid_amount, Decimal('66.666'))
        self.assertEqual(tv.remaining_amount, Decimal('33.334'))
        self.assertEqual(tv.progress_percentage, 66.7)

    def test_plan_without_later_expenses_is_not_open(self):
        self.assertEqual(open_installments(self.user, 2026, 3)['count'], 0)

    def test_most_advanced_plans_come_first(self):
        self.plan('Sofá', [date(2026, m, 1) for m in (2, 3, 4, 5)], '25')
        names = [item.description for item in open_installments(self.user, 2026, 2)['installments']]
        self.assertEqual(names, ['TV', 'Sofá'])

    def test_other_users_plans_are_ignored(self):
        self.plan('Bike', [date(2026, m, 10) for m in (1, 2, 3)], '33.333', user=User.objects.create_user(username='other'))
        self.assertEqual([i.description for i in open_installments(self.user, 2026, 2)['installments']], ['TV'])

    def test_parcelas_tab_shows_remaining_in_reais(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard_installments'), {'month': 2, 'year': 2026})
        self.assertContains(response, 'R$\xa033,33')
