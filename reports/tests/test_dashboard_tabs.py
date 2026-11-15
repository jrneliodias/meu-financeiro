from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, CategoryBudgetEstimate, Expense, PaymentMethod

TABS = ['expense_report', 'dashboard_spending', 'dashboard_categories',
        'dashboard_installments', 'dashboard_expenses']


class DashboardTabsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p')
        self.client.login(username='u', password='p')
        cat = Category.objects.create(name='Mercado', type='expense')
        pm = PaymentMethod.objects.create(name='Pix', start_billing_day=1)
        Expense.objects.create(user=self.user, description='Feira', amount=Decimal('42.00'),
                               date=date(2026, 10, 3), category=cat, payment_method=pm)

    def test_login_required(self):
        self.client.logout()
        for name in TABS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_every_tab_renders_and_marks_itself_active(self):
        for name in TABS:
            response = self.client.get(reverse(name), {'month': 10, 'year': 2026})
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'aria-current="page"')
            # o filtro de mês/ano é repassado aos links das outras abas
            self.assertContains(response, 'month=10&year=2026')

    def test_expenses_tab_lists_month_expenses(self):
        response = self.client.get(reverse('dashboard_expenses'), {'month': 10, 'year': 2026})
        self.assertContains(response, 'Feira')

    def test_home_does_not_compute_other_tabs(self):
        response = self.client.get(reverse('expense_report'), {'month': 10, 'year': 2026})
        for key in ('daily_spending_data', 'installments_progress', 'monthly_expenses_queryset',
                    'formatted_expenses_by_category'):
            self.assertNotIn(key, response.context)

    def test_notification_bell_once_on_every_tab(self):
        for name in TABS:
            response = self.client.get(reverse(name), {'month': 10, 'year': 2026})
            self.assertContains(response, 'id="payment-notifications-toggle"', count=1, msg_prefix=name)

    def test_home_has_both_charts(self):
        response = self.client.get(reverse('expense_report'), {'month': 10, 'year': 2026})
        self.assertContains(response, 'id="expenseIncomeTotalChart"')
        self.assertContains(response, 'id="calculatedPaymentMethodExpenseChart"')

    def test_categories_has_no_payment_chart(self):
        response = self.client.get(reverse('dashboard_categories'), {'month': 10, 'year': 2026})
        self.assertNotContains(response, 'calculatedPaymentMethodExpenseChart')

    def test_fit_screen_only_on_resumo_and_gastos(self):
        for name in TABS:
            response = self.client.get(reverse(name), {'month': 10, 'year': 2026})
            expected = name in ('expense_report', 'dashboard_spending')
            self.assertEqual(bool(response.context.get('fit_screen')), expected, name)

    def test_monthly_estimate_card_lives_on_gastos_not_resumo(self):
        CategoryBudgetEstimate.objects.create(
            user=self.user, category=Category.objects.get(name='Mercado'),
            amount=Decimal('500.00'), month=10, year=2026)
        card = 'reports/components/budget_estimate_card.html'
        gastos = self.client.get(reverse('dashboard_spending'), {'month': 10, 'year': 2026})
        resumo = self.client.get(reverse('expense_report'), {'month': 10, 'year': 2026})
        self.assertTemplateUsed(gastos, card)
        self.assertTemplateNotUsed(resumo, card)
        # os cards de total esperado/estimado continuam no resumo
        self.assertTemplateUsed(resumo, 'reports/components/estimated_expenses_card.html')
        self.assertEqual(gastos.context['budget_summary'].total_estimated, Decimal('500.00'))

    def test_spent_today_card_links_to_todays_expense_list(self):
        from datetime import date as d
        html = self.client.get(reverse('expense_report'), {'month': 10, 'year': 2026}).content.decode()
        self.assertIn(f"{reverse('expense_list_page')}?date={d.today().isoformat()}", html)

    def test_link_cards_have_a_subtle_chevron_hint(self):
        html = self.client.get(reverse('expense_report'), {'month': 10, 'year': 2026}).content.decode()
        # gasto hoje, parcelas do mês e total esperado
        self.assertEqual(html.count('fa-chevron-right absolute'), 3)
