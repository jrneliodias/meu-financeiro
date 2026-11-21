"""
Testes da cópia de estimativas do mês anterior (registers.budget_copy e views).
"""

import re
from decimal import Decimal

from django.contrib import messages as django_messages
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.budget_copy import CopyItem, CopyResult, copy_candidates, copy_estimates
from registers.models import Category, CategoryBudgetEstimate


def make_estimate(user, category, month, year, amount='100.00'):
    return CategoryBudgetEstimate.objects.create(
        user=user, category=category, month=month, year=year, amount=Decimal(amount),
    )


class CopyCandidatesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.other_user = User.objects.create_user(username='otheruser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')

    def source(self, month, year):
        candidates = copy_candidates(self.user, year, month)
        return candidates and (candidates.source_month, candidates.source_year)

    def test_source_is_latest_earlier_month_skipping_empty_ones(self):
        make_estimate(self.user, self.market, 7, 2026)
        make_estimate(self.user, self.market, 8, 2026)

        self.assertEqual(self.source(10, 2026), (8, 2026))

    def test_source_crosses_year(self):
        make_estimate(self.user, self.market, 12, 2026)

        self.assertEqual(self.source(1, 2027), (12, 2026))

    def test_same_and_future_months_are_not_sources(self):
        make_estimate(self.user, self.market, 10, 2026)
        make_estimate(self.user, self.market, 11, 2026)

        self.assertIsNone(self.source(10, 2026))

    def test_other_users_estimates_are_not_sources(self):
        make_estimate(self.other_user, self.market, 8, 2026)

        self.assertIsNone(self.source(10, 2026))

    def test_splits_copyable_and_existing_ordered_by_category_name(self):
        pharmacy = Category.objects.create(name='Farmácia', type='expense')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, pharmacy, 8, 2026, '50.00')
        make_estimate(self.user, self.uber, 10, 2026, '300.00')
        make_estimate(self.other_user, self.market, 10, 2026)  # another user's target doesn't block

        candidates = copy_candidates(self.user, 2026, 10)

        self.assertEqual([e.category for e in candidates.copyable], [pharmacy, self.market])
        self.assertEqual([e.category for e in candidates.already_existing], [self.uber])


class CopyEstimatesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        self.pharmacy = Category.objects.create(name='Farmácia', type='expense')

    def copy(self, *items):
        return copy_estimates(self.user, 2026, 10, [CopyItem(category.id, Decimal(amount)) for category, amount in items])

    def target_amount(self, category):
        return CategoryBudgetEstimate.objects.get(user=self.user, category=category, month=10, year=2026).amount

    def test_skips_existing_categories_without_overwriting(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        # Created in the target after the page was loaded (between the GET and the POST).
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        result = self.copy((self.market, '698.00'), (self.uber, '999.00'))

        self.assertEqual(result, CopyResult(created=1, skipped=1))
        self.assertEqual(self.target_amount(self.uber), Decimal('300.00'))

    def test_ignores_categories_not_in_source(self):
        make_estimate(self.user, self.market, 8, 2026)

        self.assertEqual(self.copy((self.pharmacy, '50.00')), CopyResult(created=0, skipped=0))
        self.assertFalse(CategoryBudgetEstimate.objects.filter(month=10, year=2026).exists())

    def test_without_source_creates_nothing(self):
        self.assertEqual(self.copy((self.market, '50.00')), CopyResult(created=0, skipped=0))
        self.assertFalse(CategoryBudgetEstimate.objects.exists())

    def test_repeated_category_is_created_once_with_last_amount(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        self.assertEqual(self.copy((self.market, '100.00'), (self.market, '200.00')), CopyResult(created=1, skipped=0))
        self.assertEqual(self.target_amount(self.market), Decimal('200.00'))


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

    def test_copy_selected_ignores_blank_amount_on_unchecked_rows(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '698.00', True),
            (self.uber, '', False),
        ]))

        self.assertRedirects(response, self.target_url, fetch_redirect_response=False)
        self.assertEqual([e.category for e in self.target_estimates()], [self.market])

    def test_copy_rejects_blank_amount_on_rows_being_copied(self):
        for action, selected in [('selected', True), ('all', False)]:
            with self.subTest(action=action):
                response = self.client.post(self.url, self.post_data([
                    (self.market, '698.00', True),
                    (self.uber, '', selected),
                ], action=action), follow=True)

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


class BudgetEstimateListCopySectionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        self.client.force_login(self.user)
        self.url = reverse('budget_estimate_list') + '?month=10&year=2026'

    def get_html(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def input_tag(self, html, name):
        """The rendered <input> with this name (what the copy form posts), or None."""
        match = re.search(rf'<input[^>]*name="{name}"[^>]*>', html)
        return match and match.group(0)

    def test_list_offers_source_rows_ticked_with_source_amount(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        html = self.get_html()

        self.assertIn('8/2026', html)  # the source month
        self.assertIn(f'action="{reverse("budget_estimate_copy")}"', html)
        self.assertIn('name="action" value="all"', html)
        self.assertIn(f'value="{self.market.id}"', self.input_tag(html, 'copy-0-category_id'))
        self.assertIn('checked', self.input_tag(html, 'copy-0-selected'))
        self.assertIn('value="698.00"', self.input_tag(html, 'copy-0-amount'))

    def test_list_shows_categories_already_in_target_as_read_only(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        html = self.get_html()

        self.assertIn(f'value="{self.market.id}"', self.input_tag(html, 'copy-0-category_id'))
        self.assertIsNone(self.input_tag(html, 'copy-1-category_id'))  # Uber is not offered for copying
        self.assertIn('R$\xa0354,00', html)  # but its source amount is listed

    def test_list_hides_copy_section_without_source(self):
        self.assertNotIn('copy-estimates-title', self.get_html())
