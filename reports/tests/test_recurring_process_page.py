from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod, RecurringExpense
from utils.tests.html import links_to, page


class RecurringProcessPageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='p', password='pw12345!')
        self.client.force_login(self.user)
        cat = Category.objects.create(name='Food', type='expense')
        method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.rec = RecurringExpense.objects.create(
            user=self.user, description='Unimed', total_amount=Decimal('100'),
            start_date=date(2024, 9, 25), category=cat, payment_method=method)
        self.url = reverse('recurring_expense_process')

    def test_get_shows_the_month_form_without_a_result(self):
        elements = page(self.client.get(self.url))
        [form] = [e for e in elements if e['tag'] == 'form' and any(f.get('name') == 'month' for f in e['inner'])]
        self.assertEqual(form['method'], 'post')
        self.assertIn('year', {field.get('name') for field in form['inner']})
        self.assertFalse([e for e in elements if e.get('role') == 'status'])

    def test_creates_an_unpaid_expense_and_is_idempotent(self):
        first = self.client.post(self.url, {'month': 11, 'year': 2026})
        self.assertContains(first, '1 despesa(s) criada(s)')
        self.assertContains(first, '0 já existente(s)')
        [expense] = Expense.objects.filter(reccurring_expense=self.rec)
        self.assertEqual((expense.date, expense.amount), (date(2026, 11, 25), Decimal('100')))
        self.assertFalse(expense.is_paid)
        self.assertIsNone(expense.paid_at)
        again = self.client.post(self.url, {'month': 11, 'year': 2026})
        self.assertContains(again, '0 despesa(s) criada(s)')
        self.assertContains(again, '1 já existente(s)')
        self.assertEqual(Expense.objects.filter(reccurring_expense=self.rec).count(), 1)

    def test_day_31_is_clamped_to_month_end(self):
        self.rec.start_date = date(2024, 1, 31)
        self.rec.save()
        self.client.post(self.url, {'month': 2, 'year': 2027})
        self.client.post(self.url, {'month': 2, 'year': 2028})
        self.assertEqual(
            sorted(Expense.objects.filter(reccurring_expense=self.rec).values_list('date', flat=True)),
            [date(2027, 2, 28), date(2028, 2, 29)])

    def test_any_expense_in_the_same_month_counts_as_generated(self):
        Expense.objects.create(user=self.user, description='Unimed', amount=Decimal('100'),
                               date=date(2026, 11, 3), reccurring_expense=self.rec)
        self.client.post(self.url, {'month': 11, 'year': 2026})
        self.assertEqual(Expense.objects.filter(reccurring_expense=self.rec).count(), 1)

    def test_invalid_month_year_returns_400(self):
        for data in ({'month': 13, 'year': 2026}, {'month': 'x', 'year': 2026}, {'year': 2026}):
            self.assertEqual(self.client.post(self.url, data).status_code, 400, data)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_list_page_links_to_process_page(self):
        self.assertTrue(links_to(page(self.client.get(reverse('recurring_expense_list'))), self.url))
