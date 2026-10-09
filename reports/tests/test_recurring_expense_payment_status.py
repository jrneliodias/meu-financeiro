"""
Tests for the fixed-expense payment status feature: repository, service,
and view/endpoint behavior for marking recurring-expense occurrences as
paid/pending.
"""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, Expense, PaymentMethod, RecurringExpense
from reports.services.recurring_expense_service import RecurringExpenseService


class ProcessRecurringExpensesPaymentStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.recurring_expense = RecurringExpense.objects.create(
            user=self.user,
            description='Netflix',
            total_amount=50,
            start_date=date(2026, 1, 5),
            category=self.category,
            payment_method=self.payment_method,
        )
        self.service = RecurringExpenseService()

    def test_generated_expense_is_not_paid(self):
        result = self.service.process_recurring_expenses_for_month(self.user, 9, 2026)

        self.assertEqual(result['created_count'], 1)
        expense = Expense.objects.get(reccurring_expense=self.recurring_expense)
        self.assertFalse(expense.is_paid)
        self.assertIsNone(expense.paid_at)


class ToggleExpensePaidTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='12345')
        self.other_user = User.objects.create_user(username='intruder', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.recurring_expense = RecurringExpense.objects.create(
            user=self.user,
            description='Netflix',
            total_amount=50,
            start_date=date(2026, 9, 5),
            category=self.category,
            payment_method=self.payment_method,
        )
        self.expense = Expense.objects.create(
            user=self.user,
            description='Netflix',
            amount=50,
            date=date(2026, 9, 5),
            category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=self.recurring_expense,
            is_paid=False,
        )
        self.service = RecurringExpenseService()

    def test_toggle_marks_expense_as_paid(self):
        updated = self.service.toggle_paid(self.expense.id, self.user)

        self.assertTrue(updated.is_paid)
        self.assertIsNotNone(updated.paid_at)

    def test_toggle_twice_marks_expense_as_pending_again(self):
        self.service.toggle_paid(self.expense.id, self.user)
        updated = self.service.toggle_paid(self.expense.id, self.user)

        self.assertFalse(updated.is_paid)
        self.assertIsNone(updated.paid_at)

    def test_cannot_toggle_another_users_expense(self):
        with self.assertRaises(Expense.DoesNotExist):
            self.service.toggle_paid(self.expense.id, self.other_user)

    def test_cannot_toggle_expense_without_recurring_link(self):
        manual_expense = Expense.objects.create(
            user=self.user,
            description='Coffee',
            amount=10,
            date=date(2026, 9, 6),
            category=self.category,
            payment_method=self.payment_method,
        )

        with self.assertRaises(Expense.DoesNotExist):
            self.service.toggle_paid(manual_expense.id, self.user)


class MonthExpensesWithStatusTest(TestCase):
    def setUp(self):
        from reports.repository.recurring_expense_repository import RecurringExpenseRepository
        self.user = User.objects.create_user(username='owner2', password='12345')
        self.other_user = User.objects.create_user(username='intruder2', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.repository = RecurringExpenseRepository()

        self.paid_recurring = RecurringExpense.objects.create(
            user=self.user, description='Netflix', total_amount=50,
            start_date=date(2026, 1, 5), category=self.category,
            payment_method=self.payment_method,
        )
        Expense.objects.create(
            user=self.user, description='Netflix', amount=50,
            date=date(2026, 9, 5), category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=self.paid_recurring, is_paid=True,
        )

        self.pending_recurring = RecurringExpense.objects.create(
            user=self.user, description='Internet', total_amount=100,
            start_date=date(2026, 1, 10), category=self.category,
            payment_method=self.payment_method,
        )
        Expense.objects.create(
            user=self.user, description='Internet', amount=100,
            date=date(2026, 9, 10), category=self.category,
            payment_method=self.payment_method,
            reccurring_expense=self.pending_recurring, is_paid=False,
        )

        RecurringExpense.objects.create(
            user=self.user, description='Gym', total_amount=80,
            start_date=date(2026, 1, 15), category=self.category,
            payment_method=self.payment_method,
        )

        RecurringExpense.objects.create(
            user=self.user, description='Old Subscription', total_amount=20,
            start_date=date(2026, 1, 20), category=self.category,
            payment_method=self.payment_method, generate_debit=False,
        )

        RecurringExpense.objects.create(
            user=self.other_user, description='Other User Rent', total_amount=999,
            start_date=date(2026, 1, 1), category=self.category,
            payment_method=self.payment_method,
        )

    def test_returns_status_per_active_recurring_expense(self):
        results = self.repository.get_month_expenses_with_status(self.user, 9, 2026)

        statuses = {entry['recurring_expense'].description: entry['status'] for entry in results}
        self.assertEqual(statuses, {
            'Netflix': 'paid',
            'Internet': 'pending',
            'Gym': 'not_generated',
        })

    def test_excludes_inactive_and_other_users_recurring_expenses(self):
        results = self.repository.get_month_expenses_with_status(self.user, 9, 2026)

        descriptions = [entry['recurring_expense'].description for entry in results]
        self.assertNotIn('Old Subscription', descriptions)
        self.assertNotIn('Other User Rent', descriptions)

    def test_bounded_query_count(self):
        with self.assertNumQueries(2):
            self.repository.get_month_expenses_with_status(self.user, 9, 2026)


class FixedExpensesSummaryPaymentStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner3', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.service = RecurringExpenseService()

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

    def test_summary_includes_status_counts_for_month(self):
        summary = self.service.get_fixed_expenses_summary(self.user, 9, 2026)

        self.assertEqual(summary['pending_count'], 1)
        self.assertEqual(summary['paid_count'], 0)
        self.assertEqual(summary['not_generated_count'], 0)
        self.assertEqual(summary['count'], 1)


from django.urls import reverse


class RecurringExpenseTogglePaidViewTest(TestCase):
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

    def test_toggle_paid_marks_expense_paid(self):
        response = self.client.post(
            reverse('recurring_expense_toggle_paid', args=[self.expense.id])
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_paid'])
        self.expense.refresh_from_db()
        self.assertTrue(self.expense.is_paid)

    def test_toggle_paid_rejects_other_users_expense(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse('recurring_expense_toggle_paid', args=[self.expense.id])
        )

        self.assertEqual(response.status_code, 404)
        self.expense.refresh_from_db()
        self.assertFalse(self.expense.is_paid)

    def test_toggle_paid_requires_post(self):
        response = self.client.get(
            reverse('recurring_expense_toggle_paid', args=[self.expense.id])
        )

        self.assertEqual(response.status_code, 405)


class RecurringExpenseListTemplateStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='listowner', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.client.force_login(self.user)

        from utils.dates import get_current_date
        self.current_year, self.current_month = get_current_date()

        self.paid_recurring = RecurringExpense.objects.create(
            user=self.user, description='Netflix', total_amount=50,
            start_date=date(2026, 1, 5), category=self.category,
            payment_method=self.payment_method,
        )
        Expense.objects.create(
            user=self.user, description='Netflix', amount=50,
            date=date(self.current_year, self.current_month, 5),
            category=self.category, payment_method=self.payment_method,
            reccurring_expense=self.paid_recurring, is_paid=True,
        )

        RecurringExpense.objects.create(
            user=self.user, description='Gym', total_amount=80,
            start_date=date(2026, 1, 15), category=self.category,
            payment_method=self.payment_method,
        )

    def test_page_shows_paid_and_not_generated_badges(self):
        # ponytail: override() only sets the active language for this thread;
        # LocaleMiddleware re-derives the request's language from the
        # Accept-Language header (session/cookie absent here) and overrides
        # it back to pt-br, so the header is what actually has to change.
        response = self.client.get(reverse('recurring_expense_list'), HTTP_ACCEPT_LANGUAGE='en')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paid')
        self.assertContains(response, 'Not generated')

    def test_pending_count_is_zero_when_nothing_pending(self):
        response = self.client.get(reverse('recurring_expense_list'))

        self.assertEqual(response.context['pending_count'], 0)

    def test_inactive_recurring_expense_with_generated_expense_shows_dash(self):
        # An inactive recurring expense can still have a real Expense (and
        # is_paid state) for this month if it was deactivated after the
        # bill was generated. It must not be mislabeled "Not generated".
        inactive_recurring = RecurringExpense.objects.create(
            user=self.user, description='Old Subscription', total_amount=30,
            start_date=date(2026, 1, 1), category=self.category,
            payment_method=self.payment_method, generate_debit=False,
        )
        Expense.objects.create(
            user=self.user, description='Old Subscription', amount=30,
            date=date(self.current_year, self.current_month, 1),
            category=self.category, payment_method=self.payment_method,
            reccurring_expense=inactive_recurring, is_paid=False,
        )

        response = self.client.get(reverse('recurring_expense_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '—')
        content = response.content.decode()
        old_subscription_index = content.index('Old Subscription')
        self.assertNotIn(
            'Not generated',
            content[old_subscription_index:old_subscription_index + 1500],
        )


class RecurringExpensePaymentStatusTranslationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='translationuser', password='12345')
        self.category = Category.objects.create(name='Food', type='expense')
        self.payment_method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.client.force_login(self.user)

    def test_not_generated_badge_is_translated_to_portuguese_by_default(self):
        RecurringExpense.objects.create(
            user=self.user, description='Gym', total_amount=80,
            start_date=date(2026, 1, 15), category=self.category,
            payment_method=self.payment_method,
        )

        response = self.client.get(reverse('recurring_expense_list'))

        self.assertContains(response, 'Não gerada')


class SetExpensePaidViewTest(RecurringExpenseTogglePaidViewTest):
    def set_paid(self, value):
        return self.client.post(
            reverse('recurring_expense_set_paid', args=[self.expense.id]),
            data={'is_paid': value}, content_type='application/json',
        )

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

    def test_rejects_manual_expense(self):
        self.expense.reccurring_expense = None
        self.expense.save()
        self.assertEqual(self.set_paid(True).status_code, 404)

    def test_requires_post_and_login(self):
        url = reverse('recurring_expense_set_paid', args=[self.expense.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.set_paid(True).status_code, 302)

    def test_checkbox_renders_persisted_state(self):
        self.set_paid(True)
        self.expense.refresh_from_db()
        from utils.dates import get_current_date
        year, month = get_current_date()
        self.expense.date = date(year, month, 5)
        self.expense.save()
        response = self.client.get(reverse('recurring_expense_list'))
        self.assertContains(response, 'expense-payment-checkbox')
        self.assertContains(response, 'checked')

    def test_monthly_table_shows_recurring_payment_controls_only(self):
        from django.template.loader import render_to_string
        manual = Expense.objects.create(
            user=self.user, description='Coffee', amount=10,
            date=date(2026, 9, 6),
        )
        self.set_paid(True)
        self.expense.refresh_from_db()
        html = render_to_string(
            'reports/components/expense_details_table.html',
            {'monthly_expenses_queryset': [self.expense, manual]},
        )
        self.assertEqual(html.count('expense-payment-checkbox'), 2)
        self.assertEqual(html.count('data-expense-id="%s"' % self.expense.id), 2)
        self.assertNotIn('data-expense-id="%s"' % manual.id, html)
        self.assertEqual(html.count('checked'), 2)
