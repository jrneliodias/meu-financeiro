from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Expense, PaymentMethod


class BillingMonthTest(TestCase):
    """The bill of month M runs from M/start_billing_day to (M+1)/(start_billing_day - 1)."""

    def _card(self, start_day, *days):
        """A card whose bill starts on `start_day`, with one expense on each of `days`."""
        user = User.objects.create_user(username=f'u{start_day}')
        card = PaymentMethod.objects.create(name=f'Card {start_day}', start_billing_day=start_day)
        for day in days:
            Expense.objects.create(user=user, description=str(day), amount=Decimal('1'), date=day, payment_method=card)

    def bill(self, year, month):
        return sorted(Expense.objects.in_billing_month(year, month).values_list('date', flat=True))

    def test_october_bill_with_start_day_3(self):
        self._card(3, date(2026, 10, 2), date(2026, 10, 3), date(2026, 11, 2), date(2026, 11, 3))
        self.assertEqual(self.bill(2026, 9), [date(2026, 10, 2)])
        self.assertEqual(self.bill(2026, 10), [date(2026, 10, 3), date(2026, 11, 2)])
        self.assertEqual(self.bill(2026, 11), [date(2026, 11, 3)])

    def test_december_bill_spills_into_next_year(self):
        self._card(3, date(2026, 12, 2), date(2026, 12, 3), date(2027, 1, 2), date(2027, 1, 3))
        self.assertEqual(self.bill(2026, 12), [date(2026, 12, 3), date(2027, 1, 2)])
        # early January belongs to the previous December's bill
        self.assertEqual(self.bill(2027, 1), [date(2027, 1, 3)])

    def test_start_day_past_month_end(self):
        # day 30 never comes in February: the January bill closes on Feb 28, the February bill opens on Mar 1
        self._card(30, date(2026, 1, 29), date(2026, 1, 30), date(2026, 2, 28),
                   date(2026, 3, 1), date(2026, 3, 29), date(2026, 3, 30))
        self.assertEqual(self.bill(2026, 1), [date(2026, 1, 30), date(2026, 2, 28)])
        self.assertEqual(self.bill(2026, 2), [date(2026, 3, 1), date(2026, 3, 29)])
        self.assertEqual(self.bill(2026, 3), [date(2026, 3, 30)])

    def test_start_day_1_is_the_calendar_month(self):
        self._card(1, date(2026, 11, 30), date(2026, 12, 1), date(2026, 12, 31), date(2027, 1, 1))
        self.assertEqual(self.bill(2026, 12), [date(2026, 12, 1), date(2026, 12, 31)])

    def test_expense_without_payment_method_uses_the_calendar_month(self):
        user = User.objects.create_user(username='no-method')
        Expense.objects.create(user=user, description='cash', amount=Decimal('1'), date=date(2026, 3, 1))
        self.assertEqual(self.bill(2026, 3), [date(2026, 3, 1)])
        self.assertEqual(self.bill(2026, 2), [])
