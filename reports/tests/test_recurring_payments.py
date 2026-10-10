from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Expense, RecurringExpense
from reports.services.recurring_payment_service import RecurringPaymentService


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
        self.service = RecurringPaymentService()
        self.client.force_login(self.user)

    def test_month_scope_counts_totals_and_bounded_queries(self):
        Expense.objects.create(user=self.user, description='Other month', amount=500,
                               date=date(2026, 9, 5), reccurring_expense=self.schedule, is_paid=False)
        Expense.objects.create(user=self.other, description='Other user', amount=500,
                               date=date(2026, 10, 5), reccurring_expense=self.schedule, is_paid=False)
        Expense.objects.create(user=self.user, description='Manual', amount=500,
                               date=date(2026, 10, 5), is_paid=False)
        with self.assertNumQueries(2):
            overview = self.service.get_overview(self.user, 10, 2026)
        self.assertEqual(overview['pending_count'], 1)
        self.assertEqual(overview['paid_count'], 1)
        self.assertEqual(overview['pending_total'], Decimal('100'))
        self.assertEqual(overview['paid_total'], Decimal('90'))

    def test_deactivated_schedule_is_excluded_from_lists_and_totals(self):
        self.schedule.generate_debit = False
        self.schedule.save()
        overview = self.service.get_overview(self.user, 10, 2026)
        self.assertEqual(overview['pending_count'], 0)
        self.assertEqual(overview['paid_count'], 0)
        self.assertEqual(overview['pending_total'], Decimal('0'))
        self.assertEqual(overview['paid_total'], Decimal('0'))
        self.assertEqual(overview['missing_count'], 0)
        response = self.client.get(reverse('recurring_payments'), {'month': 10, 'year': 2026})
        self.assertNotContains(response, 'Internet')
        self.assertTrue(Expense.objects.filter(pk=self.pending.pk).exists())

    def test_missing_excludes_future_and_other_user_schedules(self):
        missing = RecurringExpense.objects.create(user=self.user, description='Gym', total_amount=50,
                                                start_date=date(2026, 10, 1))
        RecurringExpense.objects.create(user=self.user, description='Future', total_amount=50,
                                       start_date=date(2026, 11, 1))
        RecurringExpense.objects.create(user=self.other, description='Private', total_amount=50,
                                       start_date=date(2026, 10, 1))
        RecurringExpense.objects.create(user=self.user, description='Inactive', total_amount=50,
                                       start_date=date(2026, 10, 1), generate_debit=False)
        overview = self.service.get_overview(self.user, 10, 2026)
        self.assertEqual(overview['missing_schedules'], [missing])
        self.assertEqual(overview['missing_count'], 1)

    def test_page_orders_pending_before_paid_and_displays_payment_date(self):
        response = self.client.get(reverse('recurring_payments'), {'month': 10, 'year': 2026})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertLess(html.index('id="pending-heading"'), html.index('id="paid-heading"'))
        self.assertContains(response, 'Pagamento: 09/10/2026')
        self.assertContains(response, 'expense-payment-checkbox', count=2)

    def test_saved_payment_moves_between_groups(self):
        url = reverse('recurring_expense_set_paid', args=[self.pending.id])
        self.assertEqual(self.client.post(url, {'is_paid': True}, content_type='application/json').status_code, 200)
        overview = self.service.get_overview(self.user, 10, 2026)
        self.assertEqual(overview['pending_count'], 0)
        self.assertEqual(overview['paid_count'], 2)
        self.client.post(url, {'is_paid': False}, content_type='application/json')
        self.assertEqual(self.service.get_overview(self.user, 10, 2026)['pending_count'], 1)

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
        self.assertEqual(response.context['pending_count'], 0)

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
        overview = self.service.get_overview(self.user, 10, 2026, today=date(2026, 10, 9))
        pending = overview['pending_expenses']
        self.assertEqual([item.pk for item in pending], [overdue.pk, today_expense.pk, self.pending.pk])
        self.assertEqual([item.due_status for item in pending], ['overdue', 'today', 'upcoming'])
        self.assertEqual(overview['paid_expenses'][0].due_status, 'paid')

    def test_page_highlights_due_date_and_urgency(self):
        from unittest.mock import patch
        with patch('reports.services.recurring_payment_service.localdate', return_value=date(2026, 10, 5)):
            response = self.client.get(reverse('recurring_payments'), {'month': 10, 'year': 2026})
        self.assertContains(response, 'Vencimento')
        self.assertContains(response, 'Vence hoje')
        self.assertContains(response, 'payment-row--today')
        self.assertNotContains(response, 'Vencida')

    def test_notifications_scope_statuses_and_no_cache(self):
        from unittest.mock import patch
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
        with patch('django.utils.timezone.localdate', return_value=date(2026, 10, 9)):
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

    def test_notification_payment_updates_summary_and_excludes_inactive(self):
        from unittest.mock import patch
        with patch('django.utils.timezone.localdate', return_value=date(2026, 10, 9)):
            self.client.post(reverse('recurring_expense_set_paid', args=[self.pending.pk]),
                             {'is_paid': True}, content_type='application/json')
            response = self.client.get(reverse('payment_notifications'))
            self.assertEqual(response.json()['pending_count'], 0)
            self.assertEqual(response.json()['overdue_count'], 0)
            self.schedule.generate_debit = False
            self.schedule.save()
            response = self.client.get(reverse('payment_notifications'))
            self.assertNotIn('Internet', response.json()['html'])

    def test_notifications_require_login_and_get(self):
        url = reverse('payment_notifications')
        self.assertEqual(self.client.post(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_main_menu_has_notification_dialog_and_one_payment_script(self):
        response = self.client.get(reverse('recurring_payments'), {'month': 10, 'year': 2026})
        self.assertContains(response, 'id="payment-notifications-toggle"')
        self.assertContains(response, '<dialog id="payment-notifications"')
        self.assertContains(response, 'js/expense_payment.js', count=1)
