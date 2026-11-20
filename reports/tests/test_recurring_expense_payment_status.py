"""
Fixed-expense payment status: the month's summaries and the endpoint/pages that mark occurrences paid/pending.
"""
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from registers.models import Category, Expense, PaymentMethod, RecurringExpense
from reports.services.recurring import fixed_expenses_summary
from utils.tests.html import links_to, page, payment_checkboxes


class FixedExpensesSummaryPaymentStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner3', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)

        recurring = RecurringExpense.objects.create(
            user=self.user, description='Netflix', total_amount=50,
            start_date=date(2026, 1, 5), category=self.category,
            payment_method=self.payment_method,
        )
        Expense.objects.create(
            user=self.user, description='Netflix', amount=50,
            date=date(2026, 9, 5), category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=recurring, is_paid=False,
        )

    def test_summary_includes_pending_count_for_month(self):
        summary = fixed_expenses_summary(self.user, 2026, 9)

        self.assertEqual(summary['pending_count'], 1)
        self.assertEqual(summary['total_amount'], Decimal('50'))


class RecurringExpenseListSummaryTest(TestCase):
    def test_summary_shows_active_total_and_this_month_pending_count(self):
        user = User.objects.create_user(username='listowner', password='12345')
        self.client.force_login(user)
        today = timezone.localdate()
        netflix = RecurringExpense.objects.create(user=user, description='Netflix', total_amount=50,
                                                  start_date=date(2026, 1, 5))
        gym = RecurringExpense.objects.create(user=user, description='Gym', total_amount=80,
                                              start_date=date(2026, 1, 15))
        RecurringExpense.objects.create(user=user, description='Old Subscription', total_amount=30,
                                        start_date=date(2026, 1, 1), generate_debit=False)
        Expense.objects.create(user=user, description='Netflix', amount=50, date=today.replace(day=5),
                               reccurring_expense=netflix, is_paid=True)
        Expense.objects.create(user=user, description='Gym', amount=80, date=today.replace(day=15),
                               reccurring_expense=gym, is_paid=False)

        response = self.client.get(reverse('recurring_expense_list'))

        self.assertContains(response, 'R$\xa0130,00')  # active only: 50 + 80
        [pending] = [e for e in page(response) if 'data-pending-count' in e]
        self.assertEqual(pending['text'].strip(), '1')


class SetExpensePaidViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='viewowner', password='12345')
        self.other_user = User.objects.create_user(username='viewintruder', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.recurring_expense = RecurringExpense.objects.create(
            user=self.user, description='Netflix', total_amount=50,
            start_date=date(2026, 1, 5), category=self.category,
            payment_method=self.payment_method,
        )
        self.expense = Expense.objects.create(
            user=self.user, description='Netflix', amount=50,
            date=date(2026, 9, 5), category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=self.recurring_expense, is_paid=False,
        )
        self.client.force_login(self.user)

    def set_paid(self, value):
        return self.client.post(
            reverse('recurring_expense_set_paid', args=[self.expense.id]),
            data={'is_paid': value}, content_type='application/json',
        )

    def test_marks_expense_paid(self):
        response = self.set_paid(True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True, 'is_paid': True})
        self.expense.refresh_from_db()
        self.assertTrue(self.expense.is_paid)
        self.assertIsNotNone(self.expense.paid_at)

    def test_repeated_request_preserves_paid_state_and_date(self):
        self.assertEqual(self.set_paid(True).status_code, 200)
        self.expense.refresh_from_db()
        paid_at = self.expense.paid_at
        self.assertEqual(self.set_paid(True).status_code, 200)
        self.expense.refresh_from_db()
        self.assertTrue(self.expense.is_paid)
        self.assertEqual(self.expense.paid_at, paid_at)
        self.assertEqual(self.set_paid(False).status_code, 200)
        self.expense.refresh_from_db()
        self.assertFalse(self.expense.is_paid)
        self.assertIsNone(self.expense.paid_at)

    def test_payment_does_not_change_another_month(self):
        other_month = Expense.objects.create(
            user=self.user, description='Netflix', amount=50,
            date=date(2026, 10, 5), reccurring_expense=self.recurring_expense,
            is_paid=False,
        )
        self.set_paid(True)
        other_month.refresh_from_db()
        self.assertFalse(other_month.is_paid)

    def test_rejects_invalid_state(self):
        for value in ['false', 1, None]:
            self.assertEqual(self.set_paid(value).status_code, 400)

    def test_rejects_other_user(self):
        self.client.force_login(self.other_user)
        self.assertEqual(self.set_paid(True).status_code, 404)
        self.expense.refresh_from_db()
        self.assertFalse(self.expense.is_paid)

    def test_rejects_manual_expense(self):
        self.expense.reccurring_expense = None
        self.expense.save()
        self.assertEqual(self.set_paid(True).status_code, 404)

    def test_requires_post_and_login(self):
        url = reverse('recurring_expense_set_paid', args=[self.expense.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.set_paid(True).status_code, 302)

    def expenses_page(self, recurring=None):
        return self.client.get(reverse(
            'recurring_expense_expenses', args=[(recurring or self.recurring_expense).id]))

    def test_expenses_page_shows_payment_state_per_expense(self):
        self.set_paid(True)
        other = Expense.objects.create(
            user=self.user, description='Netflix', amount=50,
            date=date(2020, 1, 5), reccurring_expense=self.recurring_expense,
            is_paid=False,
        )
        response = self.expenses_page()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment_checkboxes(page(response)), {
            (self.expense.id, True, reverse('recurring_expense_set_paid', args=[self.expense.id])),
            (other.id, False, reverse('recurring_expense_set_paid', args=[other.id])),
        })

    def test_expenses_page_is_owner_only_and_requires_login(self):
        self.client.force_login(self.other_user)
        self.assertEqual(self.expenses_page().status_code, 404)
        self.client.logout()
        self.assertEqual(self.expenses_page().status_code, 302)

    def test_expenses_page_escapes_description(self):
        self.expense.description = '"><img src=x onerror=alert(1)>'
        self.expense.save()
        response = self.expenses_page()
        self.assertNotContains(response, '<img src=x')
        self.assertContains(response, '&lt;img src=x')

    def test_expenses_page_shows_empty_state(self):
        empty = RecurringExpense.objects.create(
            user=self.user, description='Gym', total_amount=80, start_date=date(2026, 1, 15),
        )
        self.assertContains(self.expenses_page(empty), 'Nenhuma despesa gerada ainda.')

    def test_list_links_to_expenses_page(self):
        elements = page(self.client.get(reverse('recurring_expense_list')))
        self.assertTrue(links_to(elements, reverse('recurring_expense_expenses', args=[self.recurring_expense.id])))

    def expenses_tab(self):
        return self.client.get(reverse('dashboard_expenses'), {'month': 9, 'year': 2026})

    def test_monthly_table_shows_recurring_payment_controls_only(self):
        manual = Expense.objects.create(
            user=self.user, description='Coffee', amount=10,
            date=date(2026, 9, 6),
        )
        self.set_paid(True)
        response = self.expenses_tab()
        self.assertContains(response, manual.description)
        self.assertEqual(payment_checkboxes(page(response)), {
            (self.expense.id, True, reverse('recurring_expense_set_paid', args=[self.expense.id])),
        })

    def test_monthly_table_formats_dates_as_dd_mm_yyyy(self):
        stamp = timezone.make_aware(datetime(2026, 11, 8, 14, 5))
        Expense.objects.filter(pk=self.expense.pk).update(created_at=stamp, updated_at=stamp)
        html = self.expenses_tab().content.decode()
        self.assertIn('05-09-2026', html)
        self.assertIn('08-11-2026 14:05', html)
