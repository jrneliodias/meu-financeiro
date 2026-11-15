from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, PaymentMethod


class ExpenseListPageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p')
        self.other = User.objects.create_user(username='o', password='p')
        self.client.login(username='u', password='p')
        self.mercado = Category.objects.create(name='Mercado', type='expense')
        self.lazer = Category.objects.create(name='Lazer', type='expense')
        self.pix = PaymentMethod.objects.create(name='Pix', start_billing_day=1)
        self.url = reverse('expense_list_page')

    def _expense(self, desc, amount, day, category=None, user=None, **kw):
        return Expense.objects.create(
            user=user or self.user, description=desc, amount=Decimal(amount),
            date=date(2026, 10, day), category=category or self.mercado,
            payment_method=self.pix, **kw)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url, {'date': '2026-10-03'}).status_code, 302)

    def test_by_date_lists_only_own_expenses_with_total(self):
        self._expense('Feira', '40.00', 3)
        self._expense('Cinema', '60.00', 3, self.lazer)
        self._expense('Outro dia', '999.00', 4)
        self._expense('De outro usuário', '500.00', 3, user=self.other)
        response = self.client.get(self.url, {'date': '2026-10-03'})
        self.assertContains(response, 'Feira')
        self.assertContains(response, 'Cinema')
        self.assertNotContains(response, 'Outro dia')
        self.assertNotContains(response, 'De outro usuário')
        self.assertEqual(response.context['total'], Decimal('100.00'))
        self.assertEqual(response.context['count'], 2)

    def test_by_category_and_month(self):
        self._expense('Feira', '40.00', 5)
        self._expense('Cinema', '60.00', 5, self.lazer)
        response = self.client.get(self.url, {
            'category_id': self.mercado.id, 'month': 10, 'year': 2026})
        self.assertContains(response, 'Feira')
        self.assertNotContains(response, 'Cinema')

    def test_installments_only(self):
        from registers.models import Installment
        plan = Installment.objects.create(
            user=self.user, description='Notebook', total_amount=Decimal('300.00'),
            total_installments=3, start_date=date(2026, 10, 1),
            category=self.mercado, payment_method=self.pix)
        self._expense('Notebook 1/3', '100.00', 5, installment_plan=plan)
        self._expense('Feira', '40.00', 5)
        response = self.client.get(self.url, {'installments': 1, 'month': 10, 'year': 2026})
        self.assertContains(response, 'Notebook 1/3')
        self.assertNotContains(response, 'Feira')

    def test_no_filter_redirects_to_despesas_tab(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('dashboard_expenses'))

    def test_invalid_params_return_400(self):
        self.assertEqual(self.client.get(self.url, {'date': 'xx'}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {'category_id': 'a', 'month': 1, 'year': 2026}).status_code, 400)

    def test_rows_have_edit_link_and_delete_button(self):
        e = self._expense('Feira', '40.00', 3)
        response = self.client.get(self.url, {'date': '2026-10-03'})
        self.assertContains(response, reverse('expense_update', args=[e.pk]))
        self.assertContains(response, f'data-expense-id="{e.pk}"')

    def test_category_without_month_lists_recent_of_that_category(self):
        for day in range(1, 4):
            self._expense(f'Mercado {day}', '10.00', day)
        self._expense('Lazer 1', '99.00', 1, self.lazer)
        response = self.client.get(self.url, {'category_id': self.mercado.id})
        self.assertEqual(response.context['count'], 3)
        self.assertNotContains(response, 'Lazer 1')
        # mais recente primeiro
        self.assertEqual(response.context['expenses'][0].description, 'Mercado 3')

    def test_back_param_only_accepts_local_urls(self):
        self._expense('Feira', '40.00', 3)
        ok = self.client.get(self.url, {'date': '2026-10-03', 'back': '/gastos/?month=10'})
        self.assertEqual(ok.context['back_url'], '/gastos/?month=10')
        evil = self.client.get(self.url, {'date': '2026-10-03', 'back': 'https://evil.example/x'})
        self.assertEqual(evil.context['back_url'], '')


class NoListModalsRegressionTest(TestCase):
    """Modais ficam só para confirmação (exceção: o pop-up do sino); nenhuma página traz os modais de lista antigos."""
    OLD_MODALS = ['expenseDetailsModal', 'categoryExpenseModal', 'installmentExpensesModal',
                  'budgetBreakdownModal', 'processRecurringModal']

    def setUp(self):
        self.user = User.objects.create_user(username='r', password='p')
        self.client.login(username='r', password='p')

    def test_pages_do_not_render_list_modals(self):
        names = ['expense_report', 'dashboard_spending', 'dashboard_categories', 'dashboard_installments',
                 'dashboard_expenses', 'recurring_expense_list', 'recurring_payments',
                 'register_expense', 'budget_breakdown', 'recurring_expense_process']
        for name in names:
            html = self.client.get(reverse(name), {'month': 10, 'year': 2026}).content.decode()
            for marker in self.OLD_MODALS:
                self.assertNotIn(marker, html, f'{name} ainda contém {marker}')

    def test_bell_opens_popup_that_links_to_monthly_payments(self):
        html = self.client.get(reverse('expense_report')).content.decode()
        self.assertIn('aria-controls="payment-notifications"', html)
        self.assertIn('<dialog id="payment-notifications"', html)
        self.assertIn(f'href="{reverse("recurring_payments")}"', html)

    def test_budget_breakdown_page_shows_totals(self):
        response = self.client.get(reverse('budget_breakdown'), {'month': 10, 'year': 2026})
        self.assertEqual(response.status_code, 200)
        self.assertIn('budget_summary', response.context)
        self.assertContains(response, 'month=10&year=2026')

    def test_home_cards_link_to_pages(self):
        html = self.client.get(reverse('expense_report'), {'month': 10, 'year': 2026}).content.decode()
        self.assertIn(reverse('budget_breakdown'), html)
        self.assertIn(reverse('expense_list_page') + '?installments=1&month=10&year=2026', html)
