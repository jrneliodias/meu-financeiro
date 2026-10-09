"""
Testes da cópia de estimativas do mês anterior (repository, service e views).
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, CategoryBudgetEstimate
from registers.repository.budget_estimate_repository import BudgetEstimateRepository
from registers.services.budget_estimate_copy_service import (
    BudgetEstimateCopyService,
    CopyItem,
    CopyResult,
)


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


class BudgetEstimateCopyServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        self.pharmacy = Category.objects.create(name='Farmácia', type='expense')
        self.service = BudgetEstimateCopyService()

    def test_get_copy_candidates_returns_none_without_source(self):
        self.assertIsNone(self.service.get_copy_candidates(self.user, 10, 2026))

    def test_get_copy_candidates_splits_copyable_and_existing(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        candidates = self.service.get_copy_candidates(self.user, 10, 2026)

        self.assertEqual((candidates.source_month, candidates.source_year), (8, 2026))
        self.assertEqual([e.category for e in candidates.copyable], [self.market])
        self.assertEqual([e.category for e in candidates.already_existing], [self.uber])

    def test_copy_estimates_creates_with_given_amounts(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        result = self.service.copy_estimates(
            self.user, 10, 2026, [CopyItem(self.market.id, Decimal('720.50'))],
        )

        self.assertEqual(result, CopyResult(created=1, skipped=0))
        created = CategoryBudgetEstimate.objects.get(user=self.user, category=self.market, month=10, year=2026)
        self.assertEqual(created.amount, Decimal('720.50'))

    def test_copy_estimates_skips_existing_categories(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        # Criada no destino depois que a página foi carregada (entre o GET e o POST).
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        result = self.service.copy_estimates(self.user, 10, 2026, [
            CopyItem(self.market.id, Decimal('698.00')),
            CopyItem(self.uber.id, Decimal('999.00')),
        ])

        self.assertEqual(result, CopyResult(created=1, skipped=1))
        uber = CategoryBudgetEstimate.objects.get(user=self.user, category=self.uber, month=10, year=2026)
        self.assertEqual(uber.amount, Decimal('300.00'))

    def test_copy_estimates_ignores_categories_not_in_source(self):
        make_estimate(self.user, self.market, 8, 2026)

        result = self.service.copy_estimates(
            self.user, 10, 2026, [CopyItem(self.pharmacy.id, Decimal('50.00'))],
        )

        self.assertEqual(result, CopyResult(created=0, skipped=0))
        self.assertFalse(CategoryBudgetEstimate.objects.filter(month=10, year=2026).exists())

    def test_copy_estimates_without_source_creates_nothing(self):
        result = self.service.copy_estimates(
            self.user, 10, 2026, [CopyItem(self.market.id, Decimal('50.00'))],
        )

        self.assertEqual(result, CopyResult(created=0, skipped=0))
        self.assertFalse(CategoryBudgetEstimate.objects.exists())

    def test_copy_estimates_dedupes_repeated_categories(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        result = self.service.copy_estimates(self.user, 10, 2026, [
            CopyItem(self.market.id, Decimal('100.00')),
            CopyItem(self.market.id, Decimal('200.00')),
        ])

        self.assertEqual(result, CopyResult(created=1, skipped=0))
        created = CategoryBudgetEstimate.objects.get(user=self.user, category=self.market, month=10, year=2026)
        self.assertEqual(created.amount, Decimal('200.00'))
