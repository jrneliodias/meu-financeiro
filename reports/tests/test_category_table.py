"""Categorias tab: spending per category and billing month of the selected year."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from registers.models import Category, Expense, PaymentMethod
from reports.services.categories import category_month_table
from utils.tests.html import links_to, page

MAY = 4  # index in the 12-month series


class CategoryTableTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='spender', password='x')
        self.card = PaymentMethod.objects.create(name='Card', start_billing_day=3)
        self.food = Category.objects.create(name='Food', type='expense')

    def spend(self, amount, day, category=None, user=None):
        Expense.objects.create(user=user or self.user, description='x', amount=Decimal(amount), date=day,
                               category=category, payment_method=self.card)

    def test_amounts_go_to_the_billing_month(self):
        self.spend('10', date(2026, 6, 2), self.food)  # before the 3rd: May's bill
        months = category_month_table(self.user, 2026)['categories'][0]['months']
        self.assertEqual((months[MAY], months[MAY + 1]), (10.0, 0.0))

    def test_categories_are_sorted_ignoring_case(self):
        self.spend('1', date(2026, 5, 10), Category.objects.create(name='Casa', type='expense'))
        self.spend('1', date(2026, 5, 10), Category.objects.create(name='banco', type='expense'))
        names = [row['name'] for row in category_month_table(self.user, 2026)['categories']]
        self.assertEqual(names, ['banco', 'Casa'])

    def test_totals_are_the_sum_of_each_month(self):
        self.spend('10', date(2026, 5, 10), self.food)
        self.spend('5', date(2026, 5, 11), Category.objects.create(name='Casa', type='expense'))
        self.assertEqual(category_month_table(self.user, 2026)['totals'][MAY], 15.0)

    def test_uncategorized_expenses_have_a_row_without_link(self):
        self.spend('10', date(2026, 5, 10), self.food)
        self.spend('7', date(2026, 5, 10))
        with translation.override('en'):
            rows = category_month_table(self.user, 2026)['categories']
        self.assertIn({'name': 'No Category', 'id': None}, [{'name': r['name'], 'id': r['id']} for r in rows])

        self.client.force_login(self.user)
        elements = page(self.client.get(reverse('dashboard_categories'), {'month': 5, 'year': 2026}))
        list_path = reverse('expense_list_page')
        self.assertTrue(links_to(elements, list_path, category_id=str(self.food.pk), month='5', year='2026'))
        self.assertEqual(links_to(elements, list_path, category_id='None'), [])

    def test_other_users_are_ignored(self):
        self.spend('10', date(2026, 5, 10), self.food, user=User.objects.create_user(username='other'))
        self.assertEqual(category_month_table(self.user, 2026)['categories'], [])
