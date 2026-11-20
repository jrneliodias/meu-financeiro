"""Budget estimates: one per user, category and month; month 1-12 and year 2000-2100."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, CategoryBudgetEstimate

DUPLICATE = 'An estimate already exists for this category this month.'


class BudgetEstimateFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='planner', password='x')
        self.client.force_login(self.user)
        self.food = Category.objects.create(name='Food', type='expense')
        self.market = Category.objects.create(name='Mercado', type='expense')

    def estimate(self, category, amount='100', user=None):
        return CategoryBudgetEstimate.objects.create(user=user or self.user, category=category,
                                                     amount=Decimal(amount), month=11, year=2026)

    # pages pick the language per request (LocaleMiddleware); ask for English like a browser would
    def create(self, category, month=11, year=2026):
        return self.client.post(reverse('budget_estimate_list'), {
            'category': category.pk, 'amount': '50', 'month': month, 'year': year}, HTTP_ACCEPT_LANGUAGE='en')

    def edit(self, estimate, category, amount='100'):
        return self.client.post(reverse('budget_estimate_update', args=[estimate.pk]), {
            'category': category.pk, 'amount': amount, 'month': 11, 'year': 2026}, HTTP_ACCEPT_LANGUAGE='en')

    def test_duplicate_category_and_month_is_rejected_on_create(self):
        self.estimate(self.food)
        response = self.create(self.food)
        self.assertContains(response, DUPLICATE)
        self.assertEqual(CategoryBudgetEstimate.objects.count(), 1)

    def test_editing_onto_an_existing_category_and_month_is_rejected(self):
        self.estimate(self.food)
        market = self.estimate(self.market)
        self.assertContains(self.edit(market, self.food), DUPLICATE)
        market.refresh_from_db()
        self.assertEqual(market.category, self.market)

    def test_editing_an_estimate_keeps_its_own_slot(self):
        food = self.estimate(self.food)
        self.assertEqual(self.edit(food, self.food, amount='250').status_code, 302)
        food.refresh_from_db()
        self.assertEqual(food.amount, Decimal('250'))

    def test_other_users_estimate_does_not_block(self):
        self.estimate(self.food, user=User.objects.create_user(username='other'))
        self.assertEqual(self.create(self.food).status_code, 302)
        self.assertTrue(CategoryBudgetEstimate.objects.filter(user=self.user, category=self.food).exists())

    def test_month_and_year_must_be_in_range(self):
        self.assertEqual(self.create(self.food, month=13).status_code, 200)
        self.assertEqual(self.create(self.food, year=1999).status_code, 200)
        self.assertFalse(CategoryBudgetEstimate.objects.exists())
