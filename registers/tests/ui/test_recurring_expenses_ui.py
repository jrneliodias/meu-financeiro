from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils.timezone import localdate

from registers.models import Category, Expense, PaymentMethod, RecurringExpense

from .base import UITestCase


class RecurringExpensesUITest(UITestCase):
    """List page + generated-expenses page (cards on mobile, table on desktop)."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='rm', password='pw12345!')
        cat = Category.objects.create(name='Saude', type='expense')
        method = PaymentMethod.objects.create(name='Nubank', start_billing_day=1)
        self.rec = RecurringExpense.objects.create(
            user=self.user, description='Unimed', total_amount=Decimal('3023.95'),
            start_date=date(2024, 9, 25), category=cat, payment_method=method)
        self.old = Expense.objects.create(
            user=self.user, description='Unimed', amount=Decimal('3023.95'),
            date=date(2025, 9, 25), category=cat, payment_method=method,
            reccurring_expense=self.rec, is_paid=False)
        self.current = Expense.objects.create(
            user=self.user, description='Unimed', amount=Decimal('3023.95'),
            date=localdate().replace(day=1), category=cat, payment_method=method,
            reccurring_expense=self.rec, is_paid=False)
        self.login(self.user)

    def expenses_url(self):
        return self.url(f'/recurring-expense/{self.rec.pk}/expenses/')

    def test_list_has_no_payment_status_or_extra_summary_cards(self):
        self.page.goto(self.url('/recurring-expenses/'))
        body = self.page.inner_text('body')
        self.assertEqual(self.page.locator('table .expense-payment-checkbox, .md\\:hidden .expense-payment-checkbox').count(), 0)
        self.assertNotIn('Despesas Inativas', body)
        self.assertNotIn('Total Geral', body)

    def test_expenses_link_opens_the_page(self):
        self.page.set_viewport_size({'width': 390, 'height': 800})
        self.page.goto(self.url('/recurring-expenses/'))
        self.page.locator('.md\\:hidden .view-expenses-btn').first.click()
        self.page.wait_for_url(lambda u: u.endswith(f'/recurring-expense/{self.rec.pk}/expenses/'))
        self.assertEqual(self.page.locator('#recurringExpenseModal').count(), 0)

    def test_desktop_shows_table_with_payment_toggle(self):
        self.page.goto(self.expenses_url())
        self.assertTrue(self.page.locator('table').is_visible())
        row = self.page.locator('table tbody tr', has_text='25/09/2025')
        self.assertEqual(row.count(), 1)  # not shifted to 24/09
        row.locator('.expense-payment-checkbox').check()
        self.page.wait_for_function(
            "[...document.querySelectorAll('table .payment-label')].some(l => l.textContent === 'Pago')")
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_paid)

    def test_mobile_shows_one_card_per_expense_in_first_screen(self):
        # Regression: the dialog buried the list below huge summary cards.
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.goto(self.expenses_url())
        self.assertFalse(self.page.locator('table').is_visible())
        cards = self.page.locator('.md\\:hidden > div')
        self.assertEqual(cards.count(), 2)
        self.assertLess(cards.first.bounding_box()['y'], 600)  # visible without scrolling
        self.assertTrue(self.page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        card = cards.filter(has_text='25/09/2025')
        card.locator('.expense-payment-checkbox').check()
        self.page.wait_for_function(
            "[...document.querySelectorAll('.md\\\\:hidden .payment-label')].some(l => l.textContent === 'Pago')")
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_paid)
        self.assertGreaterEqual(card.locator('.payment-control--swatch').bounding_box()['height'], 44)

    def test_payment_control_has_no_visible_text_and_is_yellow_or_green(self):
        self.page.goto(self.expenses_url())
        row = self.page.locator('table tbody tr', has_text='25/09/2025')
        control = row.locator('.payment-control--swatch')
        bg = lambda: control.evaluate('e => getComputedStyle(e).backgroundColor')
        self.assertEqual(bg(), 'rgb(234, 179, 8)')  # yellow: pending
        self.assertLessEqual(control.locator('.payment-label').bounding_box()['width'], 1)
        row.locator('.expense-payment-checkbox').check()
        self.page.mouse.move(0, 0)  # leave hover; wait out the colour transition
        self.page.wait_for_function(
            "[...document.querySelectorAll('table .payment-control--swatch')]"
            ".some(e => getComputedStyle(e).backgroundColor === 'rgb(22, 163, 74)')")
        self.assertEqual(bg(), 'rgb(22, 163, 74)')  # green: paid

    def test_mobile_touch_targets_are_at_least_44px(self):
        # Regression: Active toggle / edit / delete / payment were too small to tap.
        self.page.set_viewport_size({'width': 390, 'height': 800})
        self.page.goto(self.url('/recurring-expenses/'))
        targets = ['.md\\:hidden .toggle-btn', '.md\\:hidden .view-expenses-btn',
                   '.md\\:hidden .delete-btn', '.md\\:hidden a[aria-label]']
        for selector in targets:
            box = self.page.locator(selector).first.bounding_box()
            self.assertGreaterEqual(box['height'], 44, selector)
            self.assertGreaterEqual(box['width'], 44, selector)
    def test_mobile_header_buttons_are_on_their_own_row_below_the_title(self):
        # Regression: title and action buttons were squeezed on one line.
        self.page.set_viewport_size({'width': 390, 'height': 800})
        self.page.goto(self.url('/recurring-expenses/'))
        title = self.page.locator('h2.text-2xl', has_text='Despesas Recorrentes').first.bounding_box()
        process = self.page.locator('button[onclick="showProcessRecurringModal()"]').bounding_box()
        add = self.page.locator('a[href="/register/recurring-expense/"], a:has(.fa-plus)').first.bounding_box()
        self.assertGreaterEqual(process['y'], title['y'] + title['height'])
        self.assertAlmostEqual(process['y'], add['y'], delta=2)  # same row
        self.assertGreaterEqual(process['height'], 44)
        self.assertGreaterEqual(add['height'], 44)
        self.assertGreaterEqual(process['width'], 120)  # no longer cramped

    def test_desktop_header_buttons_stay_beside_the_title(self):
        self.page.goto(self.url('/recurring-expenses/'))
        title = self.page.locator('h2.text-2xl', has_text='Despesas Recorrentes').first.bounding_box()
        process = self.page.locator('button[onclick="showProcessRecurringModal()"]').bounding_box()
        self.assertLess(process['y'], title['y'] + title['height'])
