from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category, Expense, Installment, PaymentMethod
from utils.tests.html import links_to, page, with_id


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
        elements = page(response)
        self.assertEqual(with_id(elements, 'list-total')[0]['text'].strip(), 'R$\xa0100,00')
        self.assertEqual(with_id(elements, 'list-count')[0]['text'].strip(), '2')

    def _groups(self, response):
        """[(heading text, [first word of each row])] of the category groups, in page order."""
        elements = page(response)
        return [(' '.join(heading['text'].split()),
                 [row['text'].split()[0] for row in section['inner'] if row.get('role') == 'listitem'])
                for section in elements if section['tag'] == 'section' and section.get('aria-labelledby')
                for heading in with_id(elements, section.get('aria-labelledby'))]

    def test_by_date_groups_by_category_largest_subtotal_first(self):
        self._expense('Feira', '40.00', 3)
        self._expense('Pão', '10.00', 3)
        self._expense('Cinema', '60.00', 3, self.lazer)
        Expense.objects.create(user=self.user, description='Avulsa', amount=Decimal('5.00'), date=date(2026, 10, 3))
        self.assertEqual(self._groups(self.client.get(self.url, {'date': '2026-10-03'})), [
            ('Lazer 1 despesa R$ 60,00', ['Cinema']),
            ('Mercado 2 despesas R$ 50,00', ['Feira', 'Pão']),
            ('Sem categoria 1 despesa R$ 5,00', ['Avulsa']),
        ])

    def test_by_category_and_month(self):
        self._expense('Feira', '40.00', 5)
        self._expense('Cinema', '60.00', 5, self.lazer)
        response = self.client.get(self.url, {
            'category_id': self.mercado.id, 'month': 10, 'year': 2026})
        self.assertContains(response, 'Feira')
        self.assertNotContains(response, 'Cinema')
        self.assertEqual(self._groups(response), [])  # one category: the page title already names it

    def test_installments_only(self):
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
        elements = page(self.client.get(self.url, {'date': '2026-10-03'}))
        # editing returns to this list
        self.assertTrue(links_to(elements, reverse('expense_update', args=[e.pk]), next=f'{self.url}?date=2026-10-03'))
        delete_url = reverse('delete_expense', args=[e.pk])
        self.assertTrue([el for el in elements if el['tag'] == 'button' and el.get('data-url') == delete_url])

    def test_category_without_month_lists_recent_of_that_category(self):
        for day in range(1, 4):
            self._expense(f'Mercado {day}', '10.00', day)
        self._expense('Lazer 1', '99.00', 1, self.lazer)
        response = self.client.get(self.url, {'category_id': self.mercado.id})
        self.assertNotContains(response, 'Lazer 1')
        # mais recente primeiro
        rows = [e['text'] for e in page(response) if e.get('role') == 'listitem']
        self.assertEqual([' '.join(row.split()[:2]) for row in rows], ['Mercado 3', 'Mercado 2', 'Mercado 1'])

    def test_back_param_only_accepts_local_urls(self):
        self._expense('Feira', '40.00', 3)

        def back_link(back):
            [link] = with_id(page(self.client.get(self.url, {'date': '2026-10-03', 'back': back})), 'list-back')
            return link['href']

        self.assertEqual(back_link('/gastos/?month=10'), '/gastos/?month=10')
        self.assertEqual(back_link('https://evil.example/x'), reverse('dashboard_expenses'))

