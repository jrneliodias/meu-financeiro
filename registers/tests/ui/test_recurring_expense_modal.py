from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils.timezone import localdate

from registers.models import Category, Expense, PaymentMethod, RecurringExpense

from .base import UITestCase


class RecurringExpenseModalUITest(UITestCase):
    """Generated-expenses dialog: table on desktop, one card each on mobile."""

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

    def open_modal(self):
        self.page.goto(self.url('/recurring-expenses/'))
        self.page.locator('.view-expenses-btn:visible').first.click()
        self.page.locator('#recurringModalContent').wait_for(state='visible')

    def test_list_has_no_payment_status_or_extra_summary_cards(self):
        self.page.goto(self.url('/recurring-expenses/'))
        body = self.page.inner_text('body')
        self.assertEqual(self.page.locator('table .expense-payment-checkbox, .md\\:hidden .expense-payment-checkbox').count(), 0)
        self.assertNotIn('Despesas Inativas', body)
        self.assertNotIn('Total Geral', body)

    def test_desktop_modal_shows_table_with_payment_toggle(self):
        self.open_modal()
        self.assertTrue(self.page.locator('#recurringExpensesList').is_visible())
        self.assertFalse(self.page.locator('#recurringExpensesCards').is_visible())
        row = self.page.locator('#recurringExpensesList tr', has_text='25/09/2025')
        self.assertEqual(row.count(), 1)  # not shifted to 24/09 by UTC parsing
        row.locator('.expense-payment-checkbox').check()
        self.page.wait_for_function(
            "document.querySelector('#recurringExpensesList .payment-label').textContent !== 'Salvando…'")
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_paid)

    def test_mobile_modal_shows_one_card_per_expense_and_toggle_saves(self):
        self.page.set_viewport_size({'width': 390, 'height': 800})
        self.open_modal()
        self.assertFalse(self.page.locator('#recurringExpensesList').is_visible())
        cards = self.page.locator('#recurringExpensesCards > div')
        self.assertEqual(cards.count(), 2)
        # no horizontal scroll inside the modal
        self.assertTrue(self.page.evaluate(
            "(() => { const c = document.getElementById('recurringExpenseContent');"
            " return c.scrollWidth <= c.clientWidth; })()"))
        card = cards.filter(has_text='25/09/2025')
        card.locator('.expense-payment-checkbox').check()
        self.page.wait_for_function(
            "[...document.querySelectorAll('#recurringExpensesCards .payment-label')]"
            ".some(l => l.textContent === 'Pago')")
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_paid)

    def test_old_month_toggle_does_not_change_pending_counter(self):
        self.open_modal()
        before = self.page.inner_text('[data-pending-count]')
        row = self.page.locator('#recurringExpensesList tr', has_text='25/09/2025')
        row.locator('.expense-payment-checkbox').check()
        self.page.wait_for_function(
            "document.querySelector('#recurringExpensesList .payment-label').textContent !== 'Salvando…'")
        self.assertEqual(self.page.inner_text('[data-pending-count]'), before)

    def test_description_with_quotes_and_markup_is_not_injected(self):
        # Regression: escaper must encode quotes (attribute context) and tags.
        self.old.description = 'x" onfocus="window.pwned=1" autofocus y=" <img src=x onerror=window.pwned=1>'
        self.old.save()
        self.open_modal()
        self.assertIsNone(self.page.evaluate('window.pwned'))
        self.assertEqual(self.page.locator('#recurringExpensesList img').count(), 0)
        label = self.page.locator('#recurringExpensesList tr', has_text='25/09/2025').locator('.expense-payment-checkbox')
        self.assertEqual(label.get_attribute('onfocus'), None)

    def test_payment_control_has_no_visible_text_and_is_yellow_or_green(self):
        # Pending = yellow, paid = green; text stays only for screen readers.
        self.open_modal()
        row = self.page.locator('#recurringExpensesList tr', has_text='25/09/2025')
        control = row.locator('.payment-control--swatch')
        bg = lambda: control.evaluate('e => getComputedStyle(e).backgroundColor')
        self.assertEqual(bg(), 'rgb(234, 179, 8)')  # yellow: pending
        label_box = control.locator('.payment-label').bounding_box()
        self.assertLessEqual(label_box['width'], 1)  # visually hidden
        row.locator('.expense-payment-checkbox').check()
        self.page.wait_for_function(
            "document.querySelector('#recurringExpensesList tr:nth-child(2) .payment-label').textContent === 'Pago'")
        self.page.mouse.move(0, 0)  # leave hover; wait out the 150ms colour transition
        self.page.wait_for_function(
            "getComputedStyle(document.querySelector('#recurringExpensesList tr:nth-child(2) .payment-control--swatch'))"
            ".backgroundColor === 'rgb(22, 163, 74)'")
        self.assertEqual(bg(), 'rgb(22, 163, 74)')  # green: paid
        self.assertEqual(control.locator('.payment-label').text_content(), 'Pago')

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
        self.page.locator('.view-expenses-btn:visible').first.click()
        self.page.locator('#recurringModalContent').wait_for(state='visible')
        for selector in ['#recurringExpensesCards .payment-control--swatch', '#recurringModalCloseBtn']:
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
