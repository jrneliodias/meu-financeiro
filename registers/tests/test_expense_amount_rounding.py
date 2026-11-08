from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from registers.forms import ExpenseForm
from registers.models import Category, PaymentMethod


class ExpenseAmountRoundingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='r')
        self.category = Category.objects.create(name='Food', type='expense')
        self.method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)

    def form(self, amount):
        return ExpenseForm(user=self.user, data={
            'description': 'x', 'amount': amount, 'installments': 1,
            'date': '2026-11-08', 'category': self.category.pk,
            'payment_method': self.method.pk,
        })

    def test_three_decimals_accepted(self):
        form = self.form('12.345')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['amount'], Decimal('12.345'))

    def test_more_than_three_decimals_rounds_half_up(self):
        form = self.form('12.3456')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['amount'], Decimal('12.346'))
        form = self.form('12,3454')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['amount'], Decimal('12.345'))

    def test_too_many_integer_digits_is_error(self):
        form = self.form('12345678.123')
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_widget_step_is_any(self):
        self.assertEqual(self.form('1').fields['amount'].widget.attrs.get('step'), 'any')
