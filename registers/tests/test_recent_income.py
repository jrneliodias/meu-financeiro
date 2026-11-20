"""
Tests for the income registration page: saving, the recent-incomes list it renders, and deleting.
"""

import re
from datetime import date, timedelta

from django.contrib import messages as django_messages
from django.contrib.auth.models import User
from django.forms import Field
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from registers.models import Category, Income


class IncomePageTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.other_user = User.objects.create_user(username='otheruser', password='12345')
        self.category = Category.objects.create(name='Salary', type='income')
        self.client.force_login(self.user)

    def income(self, user=None, description='Paycheck', amount=1000):
        return Income.objects.create(
            user=user or self.user, description=description, amount=amount,
            date=date(2026, 7, 1), category=self.category,
        )


class RecentIncomesTest(IncomePageTestCase):
    def recent(self):
        """Descriptions of the recent incomes listed under the form, in page order."""
        html = self.client.get(reverse('register_income')).content.decode()
        return re.findall(r'data-description="([^"]*)"', html)

    def test_lists_only_own_incomes(self):
        self.income(description='Paycheck')
        self.income(user=self.other_user, description='Other income')

        self.assertEqual(self.recent(), ['Paycheck'])

    def test_lists_latest_ten_most_recently_updated_first(self):
        incomes = [self.income(description=f'Income {i}') for i in range(11)]
        start = timezone.now()
        for minutes, income in enumerate(incomes):
            Income.objects.filter(pk=income.pk).update(updated_at=start + timedelta(minutes=minutes))

        self.assertEqual(self.recent(), [f'Income {i}' for i in range(10, 0, -1)])

    def test_renders_formatted_amount_date_and_fill_data(self):
        self.income(amount='1234.50')

        response = self.client.get(reverse('register_income'))

        self.assertContains(response, 'R$\xa01.234,50')
        self.assertContains(response, '01/07/2026')
        # What "Use" copies into the form.
        self.assertContains(response, 'data-amount="1234.500"')
        self.assertContains(response, 'data-date="2026-07-01"')
        self.assertContains(response, f'data-category-id="{self.category.id}"')


class RegisterIncomeTest(IncomePageTestCase):
    def post(self, **data):
        return self.client.post(reverse('register_income'), data, follow=True)

    def test_successful_post_saves_and_redirects_with_success_message(self):
        response = self.post(description='Paycheck', amount='1000', date='2026-07-01', category=self.category.id)

        self.assertRedirects(response, reverse('register_income'))
        self.assertEqual(Income.objects.get().user, self.user)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].level, django_messages.SUCCESS)
        self.assertIn('Paycheck', str(messages[0]))

    def test_missing_category_shows_form_error(self):
        response = self.post(description='Pay', amount='10', date='2026-11-08')

        self.assertContains(response, Field.default_error_messages['required'])
        self.assertFalse(Income.objects.exists())


class DeleteIncomeTest(IncomePageTestCase):
    def test_deletes_own_income(self):
        income = self.income()

        response = self.client.post(reverse('delete_income', args=[income.id]))

        self.assertTrue(response.json()['success'])
        self.assertFalse(Income.objects.filter(id=income.id).exists())

    def test_other_users_income_is_not_found(self):
        income = self.income(user=self.other_user)

        response = self.client.post(reverse('delete_income', args=[income.id]))

        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())
        self.assertTrue(Income.objects.filter(id=income.id).exists())
