"""
Tests for the recent-incomes repository and service.
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, Income
from registers.repository.recent_income_repository import RecentIncomeRepository
from registers.services.recent_income_service import RecentIncomeService


class RecentIncomeRepositoryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.other_user = User.objects.create_user(username='otheruser', password='12345')
        self.category = Category.objects.create(name='Salary', type='income')
        self.repository = RecentIncomeRepository()

    def test_get_recent_incomes_for_user_excludes_other_users(self):
        Income.objects.create(
            user=self.user, description='Paycheck', amount=1000,
            date=date(2026, 7, 1), category=self.category,
        )
        Income.objects.create(
            user=self.other_user, description='Other income', amount=500,
            date=date(2026, 7, 1), category=self.category,
        )

        incomes = list(self.repository.get_recent_incomes_for_user(self.user))

        self.assertEqual(len(incomes), 1)
        self.assertEqual(incomes[0].description, 'Paycheck')

    def test_get_recent_incomes_for_user_respects_limit(self):
        for i in range(3):
            Income.objects.create(
                user=self.user, description=f'Income {i}', amount=100,
                date=date(2026, 7, 1), category=self.category,
            )

        incomes = list(self.repository.get_recent_incomes_for_user(self.user, limit=2))

        self.assertEqual(len(incomes), 2)

    def test_get_income_by_id_for_user_returns_none_for_other_users_income(self):
        income = Income.objects.create(
            user=self.other_user, description='Other income', amount=500,
            date=date(2026, 7, 1), category=self.category,
        )

        result = self.repository.get_income_by_id_for_user(income.id, self.user)

        self.assertIsNone(result)

    def test_get_income_by_id_for_user_returns_matching_income(self):
        income = Income.objects.create(
            user=self.user, description='Paycheck', amount=1000,
            date=date(2026, 7, 1), category=self.category,
        )

        result = self.repository.get_income_by_id_for_user(income.id, self.user)

        self.assertEqual(result, income)


class RecentIncomeServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Salary', type='income')
        self.service = RecentIncomeService()

    def test_get_recent_incomes_formats_currency_and_date(self):
        Income.objects.create(
            user=self.user, description='Paycheck', amount='1234.50',
            date=date(2026, 7, 1), category=self.category,
        )

        incomes = self.service.get_recent_incomes(self.user)

        self.assertEqual(len(incomes), 1)
        income = incomes[0]
        self.assertEqual(income['description'], 'Paycheck')
        self.assertEqual(income['amount_formatted'], 'R$ 1.234,50')
        self.assertEqual(income['date_formatted'], '01/07/2026')
        self.assertEqual(income['category_name'], 'Salary')

    def test_get_income_for_autofill_returns_none_when_not_found(self):
        result = self.service.get_income_for_autofill(999999, self.user)

        self.assertIsNone(result)

    def test_get_income_for_autofill_returns_form_fields(self):
        income = Income.objects.create(
            user=self.user, description='Paycheck', amount='1234.50',
            date=date(2026, 7, 1), category=self.category,
        )

        result = self.service.get_income_for_autofill(income.id, self.user)

        self.assertEqual(result['description'], 'Paycheck')
        self.assertEqual(result['amount'], '1234.500')
        self.assertEqual(result['date'], '2026-07-01')
        self.assertEqual(result['category_id'], self.category.id)
