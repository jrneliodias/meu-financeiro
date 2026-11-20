from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate

from registers.models import Category, CategoryBudgetEstimate, Expense, PaymentMethod
from utils.tests.html import links_to, page, with_id

TABS = ['expense_report', 'dashboard_spending', 'dashboard_categories',
        'dashboard_installments', 'dashboard_expenses']


class DashboardTabsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p')
        self.client.login(username='u', password='p')
        self.mercado = Category.objects.create(name='Mercado', type='expense')
        self.pix = PaymentMethod.objects.create(name='Pix', start_billing_day=1)
        Expense.objects.create(user=self.user, description='Feira', amount=Decimal('42.00'),
                               date=date(2026, 10, 3), category=self.mercado, payment_method=self.pix)

    def _get(self, name):
        return self.client.get(reverse(name), {'month': 10, 'year': 2026})

    def test_login_required(self):
        self.client.logout()
        for name in TABS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_every_tab_renders_and_marks_itself_active(self):
        for name in TABS:
            response = self._get(name)
            self.assertEqual(response.status_code, 200, name)
            elements = page(response)
            current = [e for e in elements if e.get('aria-current') == 'page']
            self.assertEqual([e['path'] for e in current], [reverse(name)], name)
            # o filtro de mês/ano é repassado aos links das outras abas
            for other in TABS:
                self.assertTrue(links_to(elements, reverse(other), month='10', year='2026'), f'{name} -> {other}')

    def test_expenses_tab_lists_month_expenses(self):
        Expense.objects.create(user=self.user, description='Padaria', amount=Decimal('9.00'),
                               date=date(2026, 11, 3), category=self.mercado, payment_method=self.pix)
        response = self._get('dashboard_expenses')
        self.assertContains(response, 'Feira')
        self.assertNotContains(response, 'Padaria')

    def test_every_page_has_one_bell_opening_the_payments_popup(self):
        for name in TABS + ['recurring_payments']:
            elements = page(self._get(name))
            [bell] = with_id(elements, 'payment-notifications-toggle')
            [popup] = with_id(elements, bell['aria-controls'])
            self.assertEqual(popup['tag'], 'dialog', name)
            self.assertTrue(links_to(popup['inner'], reverse('recurring_payments')), name)

    def test_home_has_both_charts(self):
        elements = page(self._get('expense_report'))
        self.assertTrue(with_id(elements, 'expenseIncomeTotalChart'))
        self.assertTrue(with_id(elements, 'calculatedPaymentMethodExpenseChart'))

    def test_month_estimates_on_gastos_and_expected_total_on_resumo(self):
        # estimate a category other than the 42 spent on Mercado: whether spending in an estimated
        # category counts again in the expected total is an open decision
        casa = Category.objects.create(name='Casa', type='expense')
        CategoryBudgetEstimate.objects.create(
            user=self.user, category=casa, amount=Decimal('500.00'), month=10, year=2026)
        # Gastos: the per-category estimates, with a link to manage the month's estimates
        gastos = self._get('dashboard_spending')
        self.assertTrue(links_to(page(gastos), reverse('budget_estimate_list'), month='10', year='2026'))
        self.assertContains(gastos, 'R$\xa0500,00')
        # Resumo: the estimated total and the expected total (500 estimated + 42 spent), linking to the breakdown
        resumo = self._get('expense_report')
        self.assertContains(resumo, 'R$\xa0500,00')
        [expected_card] = links_to(page(resumo), reverse('budget_breakdown'), month='10', year='2026')
        self.assertIn('R$\xa0542,00', expected_card['text'])

    def test_budget_breakdown_page_shows_totals_and_returns_to_resumo(self):
        CategoryBudgetEstimate.objects.create(
            user=self.user, category=self.mercado, amount=Decimal('500.00'), month=10, year=2026)
        response = self._get('budget_breakdown')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'R$\xa0500,00')
        # without ?back= the back link returns to the Resumo of the same month
        self.assertTrue(links_to(page(response), reverse('expense_report'), month='10', year='2026'))

    def test_link_cards_have_a_subtle_chevron_hint(self):
        elements = page(self._get('expense_report'))
        list_url = reverse('expense_list_page')
        cards = (links_to(elements, list_url, date=localdate().isoformat())  # gasto hoje
                 + links_to(elements, list_url, installments='1')  # parcelas do mês
                 + links_to(elements, reverse('budget_breakdown')))  # total esperado
        self.assertEqual(len(cards), 3)
        for card in cards:
            self.assertTrue(any('fa-chevron-right' in (e.get('class') or '') for e in card['inner']), card['href'])
