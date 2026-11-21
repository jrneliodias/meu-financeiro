"""Which recurring expenses are due in a month, and what they cost (IOF included)."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod, RecurringExpense
from utils.tests.html import page


class RecurringDueTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='subscriber', password='x')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='Assinaturas', type='expense')
        self.card = PaymentMethod.objects.create(name='Card', start_billing_day=1)
        self.spotify = self.schedule('Spotify', '100', date(2026, 5, 10), is_international=True)

    def schedule(self, description, amount, start, user=None, **fields):
        return RecurringExpense.objects.create(
            user=user or self.user, description=description, total_amount=Decimal(amount), start_date=start,
            category=self.category, payment_method=self.card, **fields)

    def process(self, month):
        return self.client.post(reverse('recurring_expense_process'), {'month': month, 'year': 2026})

    def test_processing_a_month_before_the_start_creates_nothing(self):
        self.process(4)
        self.assertFalse(Expense.objects.exists())

    def test_processing_the_start_month_creates_the_charged_amount(self):
        self.process(5)
        expense = Expense.objects.get()
        self.assertEqual((expense.date, expense.amount, expense.is_paid), (date(2026, 5, 10), Decimal('103.50'), False))

    def test_inactive_schedules_are_not_generated(self):
        self.spotify.generate_debit = False
        self.spotify.save()
        self.process(5)
        self.assertFalse(Expense.objects.exists())

    def test_fixed_card_and_list_total_include_iof(self):
        self.schedule('Gym', '50', date(2026, 1, 5))
        elements = page(self.client.get(reverse('expense_report'), {'month': 5, 'year': 2026},
                                        HTTP_ACCEPT_LANGUAGE='en'))
        label = next(i for i, e in enumerate(elements) if e['tag'] == 'p' and e['text'].strip() == 'Fixed Expenses:')
        fixed_card_amount = next(e for e in elements[label:] if e['tag'] == 'span')
        self.assertEqual(fixed_card_amount['text'].strip(), 'R$\xa0153,50')
        self.assertContains(self.client.get(reverse('recurring_expense_list')), 'R$\xa0153,50')

    def test_toggle_switches_generation_and_is_owner_only(self):
        url = reverse('recurring_expense_toggle', args=[self.spotify.pk])
        self.assertIs(self.client.post(url).json()['generate_debit'], False)
        self.assertIs(self.client.post(url).json()['generate_debit'], True)
        other = self.schedule('Netflix', '40', date(2026, 1, 1), user=User.objects.create_user(username='other'))
        response = self.client.post(reverse('recurring_expense_toggle', args=[other.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())
        other.refresh_from_db()
        self.assertTrue(other.generate_debit)

    def test_recurring_from_expense_copies_description_amount_date_category_and_method(self):
        self.client.post(reverse('register_expense'), {
            'description': 'Academia', 'amount': '89.90', 'installments': '1', 'date': '2026-07-15',
            'category': self.category.pk, 'payment_method': self.card.pk, 'is_recurring': 'on',
        })
        schedule = RecurringExpense.objects.get(description='Academia')
        self.assertEqual(
            (schedule.user, schedule.total_amount, schedule.start_date, schedule.category, schedule.payment_method),
            (self.user, Decimal('89.90'), date(2026, 7, 15), self.category, self.card))
