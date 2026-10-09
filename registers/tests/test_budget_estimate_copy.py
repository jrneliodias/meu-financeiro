"""
Testes da cópia de estimativas do mês anterior (repository, service e views).
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, CategoryBudgetEstimate
from registers.repository.budget_estimate_repository import BudgetEstimateRepository


def make_estimate(user, category, month, year, amount='100.00'):
    return CategoryBudgetEstimate.objects.create(
        user=user, category=category, month=month, year=year, amount=Decimal(amount),
    )


class BudgetEstimateRepositoryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.other_user = User.objects.create_user(username='otheruser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        self.repository = BudgetEstimateRepository()

    def test_find_latest_month_before_skips_empty_months(self):
        make_estimate(self.user, self.market, 8, 2026)

        self.assertEqual(self.repository.find_latest_month_before(self.user, 10, 2026), (8, 2026))

    def test_find_latest_month_before_crosses_year(self):
        make_estimate(self.user, self.market, 12, 2026)

        self.assertEqual(self.repository.find_latest_month_before(self.user, 1, 2027), (12, 2026))

    def test_find_latest_month_before_ignores_same_and_future_months(self):
        make_estimate(self.user, self.market, 10, 2026)
        make_estimate(self.user, self.market, 11, 2026)

        self.assertIsNone(self.repository.find_latest_month_before(self.user, 10, 2026))

    def test_find_latest_month_before_ignores_other_users(self):
        make_estimate(self.other_user, self.market, 8, 2026)

        self.assertIsNone(self.repository.find_latest_month_before(self.user, 10, 2026))

    def test_get_category_ids_for_month(self):
        make_estimate(self.user, self.market, 10, 2026)
        make_estimate(self.user, self.uber, 9, 2026)
        make_estimate(self.other_user, self.uber, 10, 2026)

        self.assertEqual(
            self.repository.get_category_ids_for_month(self.user, 10, 2026),
            {self.market.id},
        )

    def test_get_for_month_orders_by_category_name(self):
        make_estimate(self.user, self.uber, 8, 2026)
        make_estimate(self.user, self.market, 8, 2026)

        names = [e.category.name for e in self.repository.get_for_month(self.user, 8, 2026)]

        self.assertEqual(names, ['Supermercado', 'Uber'])
