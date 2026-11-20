"""Gastos tab: daily spending of the last N days up to today, with a 7-day moving average."""
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense
from reports.services.daily import daily_spending
from utils.tests.clock import at, today_is


class DailySpendingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='daily', password='x')
        self.food = Category.objects.create(name='Food', type='expense')

    def spend(self, amount, day, category=None, user=None):
        Expense.objects.create(user=user or self.user, description='x', amount=Decimal(amount), date=day,
                               category=category or self.food)

    def test_series_covers_the_last_n_days_including_today(self):
        with today_is(date(2026, 3, 10)):
            data = daily_spending(self.user, days=7)
        self.assertEqual(len(data['labels']), 8)
        self.assertEqual((data['labels'][0], data['labels'][-1]), ('2026-03-03', '2026-03-10'))
        self.assertEqual(data['dailyExpenses'], [0.0] * 8)

    def test_moving_average_uses_seven_days_and_a_shorter_window_at_the_start(self):
        self.spend('14', date(2026, 3, 3))
        self.spend('7', date(2026, 3, 10))
        with today_is(date(2026, 3, 10)):
            averages = daily_spending(self.user, days=7)['movingAverages']
        self.assertEqual(averages[:2], [14.0, 7.0])
        self.assertEqual(averages[-1], 1.0)  # Mar 4..10: only the 7

    def test_category_filter_and_other_users(self):
        other_category = Category.objects.create(name='Fun', type='expense')
        self.spend('5', date(2026, 3, 10))
        self.spend('9', date(2026, 3, 10), category=other_category)
        self.spend('11', date(2026, 3, 10), user=User.objects.create_user(username='other'))
        with today_is(date(2026, 3, 10)):
            self.assertEqual(daily_spending(self.user, days=7)['dailyExpenses'][-1], 14.0)
            self.assertEqual(daily_spending(self.user, days=7, category=self.food)['dailyExpenses'][-1], 5.0)

    def test_today_follows_sao_paulo_time(self):
        # 02:00 UTC on Mar 11 is still 23:00 on Mar 10 in São Paulo
        with at(datetime(2026, 3, 11, 2, 0, tzinfo=dt_timezone.utc)):
            self.assertEqual(daily_spending(self.user, days=7)['labels'][-1], '2026-03-10')

    def test_ajax_accepts_only_the_offered_periods_and_expense_categories(self):
        self.client.force_login(self.user)
        url = reverse('daily_spending_data_ajax')
        income = Category.objects.create(name='Salary', type='income')
        self.assertEqual(self.client.get(url, {'days': 5}).status_code, 400)
        self.assertEqual(self.client.get(url, {'days': 7, 'category_id': income.pk}).status_code, 400)
        response = self.client.get(url, {'days': 7, 'category_id': self.food.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {'labels', 'dailyExpenses', 'movingAverages'})
