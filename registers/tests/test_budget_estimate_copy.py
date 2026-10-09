"""
Testes da cópia de estimativas do mês anterior (repository, service e views).
"""

from decimal import Decimal

from django.contrib import messages as django_messages
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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


class BudgetEstimateCopyViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        self.client.force_login(self.user)
        self.url = reverse('budget_estimate_copy')
        self.target_url = reverse('budget_estimate_list') + '?month=10&year=2026'

    def post_data(self, rows, action='selected', month='10', year='2026'):
        """rows: lista de (categoria, valor, marcada)."""
        data = {
            'month': month,
            'year': year,
            'action': action,
            'copy-TOTAL_FORMS': str(len(rows)),
            'copy-INITIAL_FORMS': str(len(rows)),
        }
        for index, (category, amount, selected) in enumerate(rows):
            data[f'copy-{index}-category_id'] = str(category.id)
            data[f'copy-{index}-amount'] = amount
            if selected:
                data[f'copy-{index}-selected'] = 'on'
        return data

    def target_estimates(self):
        return CategoryBudgetEstimate.objects.filter(user=self.user, month=10, year=2026)

    def test_copy_selected_creates_only_checked_rows(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '720.00', True),
            (self.uber, '354.00', False),
        ]))

        self.assertRedirects(response, self.target_url, fetch_redirect_response=False)
        self.assertEqual([e.category for e in self.target_estimates()], [self.market])
        self.assertEqual(self.target_estimates().get().amount, Decimal('720.00'))

    def test_copy_all_ignores_checkboxes(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '700.00', False),
            (self.uber, '360.00', False),
        ], action='all'))

        self.assertRedirects(response, self.target_url, fetch_redirect_response=False)
        amounts = {e.category_id: e.amount for e in self.target_estimates()}
        self.assertEqual(amounts, {self.market.id: Decimal('700.00'), self.uber.id: Decimal('360.00')})

    def test_copy_shows_success_message_with_counts(self):
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        response = self.client.post(self.url, self.post_data([
            (self.market, '698.00', True),
            (self.uber, '354.00', True),
        ]), follow=True)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].level, django_messages.SUCCESS)

    def test_copy_with_nothing_selected_shows_error(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '698.00', False),
        ]), follow=True)

        self.assertFalse(self.target_estimates().exists())
        messages = list(response.context['messages'])
        self.assertEqual(messages[0].level, django_messages.ERROR)

    def test_copy_rejects_negative_amount(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '-1', True),
        ]), follow=True)

        self.assertFalse(self.target_estimates().exists())
        messages = list(response.context['messages'])
        self.assertEqual(messages[0].level, django_messages.ERROR)

    def test_copy_ignores_blank_extra_rows(self):
        data = self.post_data([], action='all')
        data['copy-TOTAL_FORMS'] = '1'
        data['copy-INITIAL_FORMS'] = '0'

        response = self.client.post(self.url, data, follow=True)

        self.assertFalse(self.target_estimates().exists())
        messages = list(response.context['messages'])
        self.assertEqual(messages[0].level, django_messages.ERROR)

    def test_copy_rejects_invalid_target_month(self):
        for month, year in [('13', '2026'), ('0', '2026'), ('abc', '2026'), ('10', '')]:
            with self.subTest(month=month, year=year):
                response = self.client.post(self.url, self.post_data(
                    [(self.market, '698.00', True)], month=month, year=year,
                ))

                self.assertEqual(response.status_code, 400)
        self.assertFalse(CategoryBudgetEstimate.objects.exclude(month=8).exists())

    def test_copy_requires_login(self):
        self.client.logout()

        response = self.client.post(self.url, self.post_data([(self.market, '698.00', True)]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        self.assertFalse(self.target_estimates().exists())

    def test_copy_get_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)


class BudgetEstimateListCopySectionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        self.client.force_login(self.user)
        self.url = reverse('budget_estimate_list') + '?month=10&year=2026'

    def test_list_shows_copy_section_from_latest_month(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        response = self.client.get(self.url)

        candidates = response.context['copy_candidates']
        self.assertEqual((candidates.source_month, candidates.source_year), (8, 2026))
        self.assertContains(response, 'Supermercado')
        self.assertContains(response, reverse('budget_estimate_copy'))
        self.assertContains(response, 'name="action" value="all"')

    def test_list_prefills_copyable_rows_checked_with_source_amount(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        response = self.client.get(self.url)

        form, estimate = response.context['copy_rows'][0]
        self.assertEqual(estimate.category, self.market)
        self.assertEqual(form.initial, {'category_id': self.market.id, 'selected': True, 'amount': Decimal('698.00')})

    def test_list_marks_existing_categories_as_read_only(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        response = self.client.get(self.url)

        self.assertEqual([e.category for _, e in response.context['copy_rows']], [self.market])
        self.assertEqual(
            [e.category for e in response.context['copy_candidates'].already_existing],
            [self.uber],
        )

    def test_list_hides_copy_section_without_source(self):
        response = self.client.get(self.url)

        self.assertIsNone(response.context['copy_candidates'])
        self.assertNotContains(response, reverse('budget_estimate_copy'))
