from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from registers.models import RecurringExpense


class RecurringExpenseIOFTest(TestCase):
    def test_charged_amount_adds_iof_only_when_international(self):
        user = User.objects.create_user(username='iof')
        recurring = RecurringExpense(user=user, description='Claude', total_amount=Decimal('114.55'),
                                     start_date=date(2026, 1, 5))
        self.assertEqual(recurring.charged_amount, Decimal('114.55'))
        recurring.is_international = True
        self.assertEqual(recurring.charged_amount, Decimal('118.56'))  # matches Nubank bill (114.55 + 4.01 IOF)
