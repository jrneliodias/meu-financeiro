"""Registering expenses and incomes: quick-fill presets and the form rules."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, Income, PaymentMethod, QuickFillPreset
from utils.tests.html import page, with_id


class ExpenseEntryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='writer', password='x')
        self.client.force_login(self.user)
        self.transport = Category.objects.create(name='Transporte', type='expense')
        self.card = PaymentMethod.objects.create(name='Card', start_billing_day=1)

    def preset(self, **fields):
        values = {'user': self.user, 'name': 'Uber', 'description': 'Uber', 'default_amount': Decimal('25'),
                  'category': self.transport, 'payment_method': self.card, **fields}
        return QuickFillPreset.objects.create(**values)

    def form_fields(self, **params):
        elements = page(self.client.get(reverse('register_expense'), params))
        description = with_id(elements, 'id_description')[0].get('value', '')
        amount = with_id(elements, 'id_amount')[0].get('value', '')
        selected = {e['text'].strip() for e in elements if e['tag'] == 'option' and 'selected' in e}
        return description, amount, selected

    def test_quick_fill_prefills_the_form_from_an_active_own_preset(self):
        description, amount, selected = self.form_fields(quick_fill=self.preset().pk)
        self.assertEqual(description, 'Uber')
        self.assertEqual(Decimal(amount), 25)
        self.assertTrue({'Transporte', 'Card'} <= selected)

    def test_quick_fill_ignores_zero_amount_and_other_users_or_inactive_presets(self):
        self.assertEqual(self.form_fields(quick_fill=self.preset(default_amount=0).pk)[:2], ('Uber', ''))
        other = self.preset(user=User.objects.create_user(username='other'), description='Taxi')
        for key in (other.pk, self.preset(is_active=False, description='Old').pk, 'abc'):
            with self.subTest(key=key):
                self.assertEqual(self.form_fields(quick_fill=key)[0], '')

    def post_expense(self, **fields):
        data = {'description': 'Lunch', 'amount': '30', 'installments': '1', 'date': '2026-03-10',
                'category': self.transport.pk, 'payment_method': self.card.pk, **fields}
        return self.client.post(reverse('register_expense'), data)

    def test_expense_form_offers_only_expense_categories(self):
        salary = Category.objects.create(name='Salário', type='income')
        self.assertEqual(self.post_expense(category=salary.pk).status_code, 200)
        self.assertFalse(Expense.objects.exists())

    def test_description_is_limited_to_100_characters(self):
        self.assertEqual(self.post_expense(description='x' * 101).status_code, 200)
        self.assertFalse(Expense.objects.exists())
        self.assertEqual(self.post_expense(description='x' * 100).status_code, 302)

    def test_income_accepts_comma_decimal_amounts(self):
        salary = Category.objects.create(name='Salário', type='income')
        self.client.post(reverse('register_income'), {
            'description': 'Salary', 'amount': '12,50', 'date': '2026-03-05', 'category': salary.pk})
        self.assertEqual(Income.objects.get().amount, Decimal('12.500'))
