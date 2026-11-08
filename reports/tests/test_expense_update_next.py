from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod


class ExpenseUpdateNextTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='n', password='pw12345!')
        self.client.force_login(self.user)
        cat = Category.objects.create(name='Food', type='expense')
        method = PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.exp = Expense.objects.create(
            user=self.user, description='x', amount=Decimal('1'), date=date(2026, 11, 8),
            category=cat, payment_method=method)
        self.url = reverse('expense_update', args=[self.exp.pk])
        self.data = {'description': 'x', 'amount': '2', 'date': '2026-11-08',
                     'category': cat.pk, 'payment_method': method.pk}

    def test_get_renders_next_as_hidden_field(self):
        r = self.client.get(self.url + '?next=/recurring-payments/')
        self.assertContains(r, 'name="next" value="/recurring-payments/"')

    def test_next_param_is_used(self):
        r = self.client.post(self.url, {**self.data, 'next': '/recurring-payments/'})
        self.assertRedirects(r, '/recurring-payments/', fetch_redirect_response=False)

    def test_external_next_is_ignored(self):
        r = self.client.post(self.url, {**self.data, 'next': 'https://evil.com'})
        self.assertRedirects(r, '/', fetch_redirect_response=False)

    def test_without_next_goes_home(self):
        r = self.client.post(self.url, self.data)
        self.assertRedirects(r, '/', fetch_redirect_response=False)
