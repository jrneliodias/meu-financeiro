from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils.timezone import localdate

from registers.models import Category, Expense, PaymentMethod, RecurringExpense

from .base import UITestCase


class NotificationEditUITest(UITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='ne', password='pw12345!')
        cat = Category.objects.create(name='Food', type='expense')
        method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        rec = RecurringExpense.objects.create(
            user=self.user, description='Luz', total_amount=Decimal('100'),
            start_date=date(2026, 1, 1), category=cat, payment_method=method)
        self.exp = Expense.objects.create(
            user=self.user, description='Luz', amount=Decimal('100'),
            date=localdate().replace(day=1), category=cat, payment_method=method,
            reccurring_expense=rec, is_paid=False)
        self.login(self.user)

    def test_notification_row_has_edit_button_that_returns_to_origin(self):
        self.page.goto(self.url('/recurring-payments/'))
        self.page.click('#payment-notifications-toggle')
        link = self.page.locator('#payment-notifications-content a[data-edit-expense]').first
        link.wait_for(state='visible')
        self.assertEqual(link.get_attribute('aria-label'), 'Editar Luz')
        link.click()
        self.page.wait_for_url(lambda u: f'/expense/{self.exp.pk}/update/' in u)
        self.page.fill('#id_amount', '120')
        self.page.click('form button[type=submit]')
        self.page.wait_for_url(lambda u: '/update/' not in u)
        self.assertIn('/recurring-payments/', self.page.url)
        self.exp.refresh_from_db()
        self.assertEqual(self.exp.amount, Decimal('120'))
