from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod, RecurringExpense
from reports.services.recurring_expense_service import RecurringExpenseService

TODAY = date(2026, 11, 8)


class RecurringSyncTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='s', password='pw12345!')
        self.food = Category.objects.create(name='Food', type='expense')
        self.home = Category.objects.create(name='Home', type='expense')
        self.method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.rec = RecurringExpense.objects.create(
            user=self.user, description='Luz', total_amount=Decimal('100'),
            start_date=date(2026, 1, 10), category=self.food, payment_method=self.method)
        self.exp = Expense.objects.create(
            user=self.user, description='Luz', amount=Decimal('100'), date=date(2026, 11, 10),
            category=self.food, payment_method=self.method, reccurring_expense=self.rec,
            is_paid=False)

    def sync(self):
        return RecurringExpenseService().sync_month_expense(self.rec, TODAY)

    def test_sync_updates_month_expense_fields(self):
        self.rec.total_amount = Decimal('150')
        self.rec.description = 'Energia'
        self.rec.category = self.home
        self.rec.save()
        self.assertEqual(self.sync(), self.exp)
        self.exp.refresh_from_db()
        self.assertEqual(self.exp.amount, Decimal('150'))
        self.assertEqual(self.exp.description, 'Energia')
        self.assertEqual(self.exp.category, self.home)

    def test_sync_keeps_paid_state(self):
        self.exp.is_paid, self.exp.paid_at = True, date(2026, 11, 5)
        self.exp.save()
        self.rec.total_amount = Decimal('150')
        self.rec.save()
        self.sync()
        self.exp.refresh_from_db()
        self.assertTrue(self.exp.is_paid)
        self.assertEqual(self.exp.paid_at, date(2026, 11, 5))

    def test_sync_clamps_day_31_in_30_day_month(self):
        self.rec.start_date = date(2026, 1, 31)
        self.rec.save()
        self.sync()
        self.exp.refresh_from_db()
        self.assertEqual(self.exp.date, date(2026, 11, 30))

    def test_sync_returns_none_without_month_expense(self):
        self.exp.delete()
        self.assertIsNone(self.sync())

    def test_sync_ignores_other_months(self):
        self.exp.date = date(2026, 10, 10)
        self.exp.save()
        self.rec.total_amount = Decimal('150')
        self.rec.save()
        self.assertIsNone(self.sync())
        self.exp.refresh_from_db()
        self.assertEqual(self.exp.amount, Decimal('100'))

    def test_sync_applies_iof_when_international(self):
        self.rec.is_international = True
        self.rec.save()
        self.sync()
        self.exp.refresh_from_db()
        self.assertEqual(self.exp.amount, self.rec.charged_amount)


class RecurringUpdateViewSyncTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='v', password='pw12345!')
        self.client.force_login(self.user)
        self.food = Category.objects.create(name='Food', type='expense')
        self.method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        today = date.today()
        self.rec = RecurringExpense.objects.create(
            user=self.user, description='Luz', total_amount=Decimal('100'),
            start_date=date(2026, 1, 1), category=self.food, payment_method=self.method)
        self.exp = Expense.objects.create(
            user=self.user, description='Luz', amount=Decimal('100'),
            date=today.replace(day=1), category=self.food, payment_method=self.method,
            reccurring_expense=self.rec)

    def post(self, sync):
        data = {'description': 'Luz', 'total_amount': '150', 'start_date': '2026-01-01',
                'category': self.food.pk, 'payment_method': self.method.pk,
                'generate_debit': 'on', 'sync_month': sync}
        return self.client.post(reverse('recurring_expense_update', args=[self.rec.pk]), data)

    def test_sync_flag_updates_both(self):
        self.post('1')
        self.rec.refresh_from_db()
        self.exp.refresh_from_db()
        self.assertEqual(self.rec.total_amount, Decimal('150'))
        self.assertEqual(self.exp.amount, Decimal('150'))

    def test_without_flag_updates_only_registry(self):
        self.post('0')
        self.rec.refresh_from_db()
        self.exp.refresh_from_db()
        self.assertEqual(self.rec.total_amount, Decimal('150'))
        self.assertEqual(self.exp.amount, Decimal('100'))

    def test_get_exposes_month_expense(self):
        r = self.client.get(reverse('recurring_expense_update', args=[self.rec.pk]))
        self.assertEqual(r.context['month_expense'], self.exp)
