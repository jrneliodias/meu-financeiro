from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils.timezone import localdate

from registers.models import Category, Expense, PaymentMethod, RecurringExpense

from .base import UITestCase


class RecurringEditSyncUITest(UITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='rec', password='pw12345!')
        cat = Category.objects.create(name='Food', type='expense')
        method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.rec = RecurringExpense.objects.create(
            user=self.user, description='Luz', total_amount=Decimal('100'),
            start_date=date(2026, 1, 1), category=cat, payment_method=method)
        self.login(self.user)

    def add_month_expense(self):
        self.exp = Expense.objects.create(
            user=self.user, description='Luz', amount=Decimal('100'),
            date=localdate().replace(day=1), category=self.rec.category,
            payment_method=self.rec.payment_method, reccurring_expense=self.rec)

    def edit_amount_and_submit(self):
        self.page.goto(self.url(f'/recurring-expense/{self.rec.pk}/update/'))
        self.page.fill('#id_total_amount', '150')
        self.page.click('form button[type=submit]')

    def amounts(self):
        self.rec.refresh_from_db()
        self.exp.refresh_from_db()
        return self.rec.total_amount, self.exp.amount

    def test_dialog_asks_and_syncs_both(self):
        self.add_month_expense()
        self.edit_amount_and_submit()
        dialog = self.page.locator('#sync-dialog')
        dialog.wait_for(state='visible')
        self.page.click('#sync-both')
        self.page.wait_for_url(lambda u: '/update/' not in u)
        self.assertEqual(self.amounts(), (Decimal('150'), Decimal('150')))

    def test_dialog_only_registry(self):
        self.add_month_expense()
        self.edit_amount_and_submit()
        self.page.locator('#sync-dialog').wait_for(state='visible')
        self.page.click('#sync-registry-only')
        self.page.wait_for_url(lambda u: '/update/' not in u)
        self.assertEqual(self.amounts(), (Decimal('150'), Decimal('100')))

    def test_no_dialog_without_month_expense(self):
        self.edit_amount_and_submit()
        self.page.wait_for_url(lambda u: '/update/' not in u)
        self.rec.refresh_from_db()
        self.assertEqual(self.rec.total_amount, Decimal('150'))

    def test_no_dialog_when_nothing_changed(self):
        self.add_month_expense()
        self.page.goto(self.url(f'/recurring-expense/{self.rec.pk}/update/'))
        self.page.click('form button[type=submit]')
        self.page.wait_for_url(lambda u: '/update/' not in u)
        self.assertEqual(self.amounts(), (Decimal('100'), Decimal('100')))
