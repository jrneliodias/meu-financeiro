from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Expense, RecurringExpense
from reports.services.recurring import month_overview
from utils.tests.clock import today_is
from utils.tests.html import page, payment_checkboxes


class RecurringPaymentsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='payment-owner')
        self.other = User.objects.create_user(username='payment-other')
        self.schedule = RecurringExpense.objects.create(
            user=self.user, description='Internet', total_amount=100,
            start_date=date(2026, 1, 5),
        )
        self.pending = Expense.objects.create(
            user=self.user, description='Internet', amount=100,
            date=date(2026, 10, 5), reccurring_expense=self.schedule, is_paid=False,
        )
        self.paid = Expense.objects.create(
            user=self.user, description='Internet paga', amount=90,
            date=date(2026, 10, 10), reccurring_expense=self.schedule,
            is_paid=True, paid_at=date(2026, 10, 9),
        )
        self.client.force_login(self.user)

    def test_month_scope_counts_and_totals(self):
        Expense.objects.create(user=self.user, description='Other month', amount=500,
                               date=date(2026, 9, 5), reccurring_expense=self.schedule, is_paid=False)
        Expense.objects.create(user=self.other, description='Other user', amount=500,
                               date=date(2026, 10, 5), reccurring_expense=self.schedule, is_paid=False)
        Expense.objects.create(user=self.user, description='Manual', amount=500,
                               date=date(2026, 10, 5), is_paid=False)
        overview = month_overview(self.user, 2026, 10)
        self.assertEqual(overview['pending_count'], 1)
        self.assertEqual(overview['paid_count'], 1)
        self.assertEqual(overview['pending_total'], Decimal('100'))
        self.assertEqual(overview['paid_total'], Decimal('90'))

    def test_deactivated_schedule_is_excluded_from_lists_and_totals(self):
        self.schedule.generate_debit = False
        self.schedule.save()
        overview = month_overview(self.user, 2026, 10)
        self.assertEqual(overview['pending_count'], 0)
        self.assertEqual(overview['paid_count'], 0)
        self.assertEqual(overview['pending_total'], Decimal('0'))
        self.assertEqual(overview['paid_total'], Decimal('0'))
        self.assertEqual(overview['missing_count'], 0)
        response = self.client.get(reverse('recurring_payments'), {'month': 10, 'year': 2026})
        self.assertNotContains(response, 'Internet')

    def test_missing_excludes_future_and_other_user_schedules(self):
        missing = RecurringExpense.objects.create(user=self.user, description='Gym', total_amount=50,
                                                start_date=date(2026, 10, 1))
        RecurringExpense.objects.create(user=self.user, description='Future', total_amount=50,
                                       start_date=date(2026, 11, 1))
        RecurringExpense.objects.create(user=self.other, description='Private', total_amount=50,
                                       start_date=date(2026, 10, 1))
        RecurringExpense.objects.create(user=self.user, description='Inactive', total_amount=50,
                                       start_date=date(2026, 10, 1), generate_debit=False)
        overview = month_overview(self.user, 2026, 10)
        self.assertEqual(overview['missing_schedules'], [missing])
        self.assertEqual(overview['missing_count'], 1)

    def test_page_lists_pending_before_paid_and_displays_payment_date(self):
        response = self.client.get(reverse('recurring_payments'), {'month': 10, 'year': 2026})
        self.assertEqual(response.status_code, 200)
        sections = [e for e in page(response) if e['tag'] == 'section']
        self.assertEqual([s['aria-labelledby'] for s in sections], ['pending-heading', 'paid-heading'])
        pending, paid = sections
        self.assertEqual(payment_checkboxes(pending['inner']),
                         {(self.pending.id, False, reverse('recurring_expense_set_paid', args=[self.pending.id]))})
        self.assertEqual(payment_checkboxes(paid['inner']),
                         {(self.paid.id, True, reverse('recurring_expense_set_paid', args=[self.paid.id]))})
        self.assertIn('Pagamento: 09/10/2026', paid['text'])

    def test_invalid_filter_and_anonymous_access(self):
        for params in [{'month': 13}, {'year': 'invalid'}, {'month': 0}, {'year': 9999}]:
            self.assertEqual(self.client.get(reverse('recurring_payments'), params).status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('recurring_payments')).status_code, 302)

    def test_empty_month_and_unknown_payment_date(self):
        self.paid.paid_at = None
        self.paid.save()
        response = self.client.get(reverse('recurring_payments'), {'month': 10, 'year': 2026})
        self.assertContains(response, 'data não registrada')
        response = self.client.get(reverse('recurring_payments'), {'month': 12, 'year': 2026})
        self.assertContains(response, 'Nenhuma despesa recorrente marcada como paga')

    def test_pending_order_prioritizes_overdue_today_then_future(self):
        self.pending.date = date(2026, 10, 20)
        self.pending.save()
        today_expense = Expense.objects.create(
            user=self.user, description='Vence hoje', amount=30,
            date=date(2026, 10, 9), reccurring_expense=self.schedule, is_paid=False,
        )
        overdue = Expense.objects.create(
            user=self.user, description='Vencida', amount=40,
            date=date(2026, 10, 2), reccurring_expense=self.schedule, is_paid=False,
        )
        overview = month_overview(self.user, 2026, 10, today=date(2026, 10, 9))
        pending = overview['pending_expenses']
        self.assertEqual([item.pk for item in pending], [overdue.pk, today_expense.pk, self.pending.pk])
        self.assertEqual([item.due_status for item in pending], ['overdue', 'today', 'upcoming'])
        self.assertEqual(overview['paid_expenses'][0].due_status, 'paid')

    def test_page_highlights_due_date_and_urgency(self):
        with today_is(date(2026, 10, 5)):
            response = self.client.get(reverse('recurring_payments'), {'month': 10, 'year': 2026})
        self.assertContains(response, 'Vencimento')
        self.assertContains(response, 'Vence hoje')
        self.assertContains(response, 'payment-row--today')
        self.assertNotContains(response, 'Vencida')

    def test_notifications_scope_statuses_and_no_cache(self):
        self.pending.date = date(2026, 10, 2)
        self.pending.save()
        upcoming = Expense.objects.create(
            user=self.user, description='Próxima conta', amount=30,
            date=date(2026, 10, 12), reccurring_expense=self.schedule, is_paid=False,
        )
        other_schedule = RecurringExpense.objects.create(
            user=self.other, description='Conta privada', total_amount=500,
            start_date=date(2026, 1, 1),
        )
        Expense.objects.create(user=self.other, description='Conta privada', amount=500,
                               date=date(2026, 10, 1), reccurring_expense=other_schedule, is_paid=False)
        with today_is(date(2026, 10, 9)):
            response = self.client.get(reverse('payment_notifications'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['pending_count'], 2)
        self.assertEqual(data['overdue_count'], 1)
        self.assertIn('Próxima a pagar:', data['html'])
        self.assertIn(upcoming.description, data['html'])
        self.assertIn('Pago em: 09/10/2026', data['html'])
        self.assertNotIn('Conta privada', data['html'])
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_notifications_require_login_and_get(self):
        url = reverse('payment_notifications')
        self.assertEqual(self.client.post(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
