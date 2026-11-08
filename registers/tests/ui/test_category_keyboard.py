from datetime import date

from django.contrib.auth.models import User

from registers.models import Category, PaymentMethod

from .base import UITestCase, expect


class CategoryKeyboardMixin:
    kind = path = next_selector = None
    prev_selector = '#id_date'

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='kb', password='pw12345!')
        for name in ('Mercado', 'Moradia', 'Mensalidade'):
            Category.objects.create(name=name, type=self.kind)
        # same names in the other type must never show up
        other = 'income' if self.kind == 'expense' else 'expense'
        Category.objects.create(name='Mouse', type=other)
        PaymentMethod.objects.create(name='Cash', start_billing_day=1)
        self.login(self.user)
        self.page.goto(self.url(self.path))
        self.input = self.page.locator('#category-search-input')
        self.options = self.page.locator('#category-dropdown li[role=option]')

    def type_in_category(self, text):
        self.input.click()
        self.input.fill('')
        self.input.press_sequentially(text)

    def focused_text(self):
        return self.page.evaluate('document.activeElement.textContent.trim()')

    def test_first_option_is_highlighted(self):
        self.type_in_category('M')
        expect(self.options).to_have_count(3)
        self.assertEqual(self.options.all_inner_texts(), ['Mensalidade', 'Mercado', 'Moradia'])
        expect(self.options.nth(0)).to_have_attribute('aria-selected', 'true')
        expect(self.options.nth(1)).to_have_attribute('aria-selected', 'false')

    def test_enter_selects_first_option_and_does_not_submit(self):
        self.type_in_category('Mo')
        expect(self.options).to_have_count(2)  # Moradia + 'Create "Mo"'
        self.input.press('Enter')
        expect(self.input).to_have_value('Moradia')
        expect(self.page.locator('#category-dropdown')).to_be_hidden()
        self.assertEqual(self.page.locator('#id_category option:checked').inner_text(), 'Moradia')
        self.assertIn(self.path, self.page.url)

    def test_enter_right_after_typing_uses_fresh_results(self):
        self.input.click()
        self.input.press_sequentially('Mor')
        self.input.press('Enter')  # before the 300ms debounce fires
        expect(self.input).to_have_value('Moradia')

    def test_enter_with_empty_list_is_harmless(self):
        errors = []
        self.page.on('pageerror', lambda e: errors.append(str(e)))
        self.type_in_category('Qqqq')
        expect(self.options).to_have_count(1)  # only the "Create" option
        self.input.fill('')
        self.input.press('Enter')
        self.page.wait_for_timeout(500)
        self.assertEqual(errors, [])
        self.assertIn(self.path, self.page.url)

    def test_tab_walks_options_then_next_field(self):
        self.type_in_category('M')
        expect(self.options).to_have_count(3)
        for expected in ('Mensalidade', 'Mercado', 'Moradia'):
            self.input.press('Tab') if expected == 'Mensalidade' else self.page.keyboard.press('Tab')
            self.assertEqual(self.focused_text(), expected)
        self.page.keyboard.press('Tab')
        expect(self.page.locator(self.next_selector)).to_be_focused()
        expect(self.page.locator('#category-dropdown')).to_be_hidden()

    def test_shift_tab_goes_back(self):
        self.type_in_category('M')
        expect(self.options).to_have_count(3)
        self.input.press('Tab')
        self.page.keyboard.press('Shift+Tab')
        expect(self.input).to_be_focused()
        self.input.press('Shift+Tab')
        expect(self.page.locator(self.prev_selector)).to_be_focused()

    def test_enter_on_focused_option_selects_and_moves_on(self):
        self.type_in_category('M')
        expect(self.options).to_have_count(3)
        self.input.press('Tab')
        self.page.keyboard.press('Tab')
        self.page.keyboard.press('Enter')
        expect(self.input).to_have_value('Mercado')
        expect(self.page.locator(self.next_selector)).to_be_focused()

    def test_arrow_keys_move_highlight(self):
        self.type_in_category('M')
        expect(self.options).to_have_count(3)
        self.input.press('ArrowDown')
        expect(self.options.nth(1)).to_have_attribute('aria-selected', 'true')
        self.input.press('Enter')
        expect(self.input).to_have_value('Mercado')

    def test_no_match_highlights_create_option(self):
        self.type_in_category('Zzz')
        expect(self.options).to_have_count(1)
        expect(self.options.nth(0)).to_have_attribute('aria-selected', 'true')
        self.input.press('Enter')
        expect(self.page.locator('#id_category')).not_to_have_value('')
        self.assertEqual(Category.objects.get(name='Zzz').type, self.kind)

    def test_only_categories_of_this_type(self):
        self.type_in_category('Mo')
        expect(self.options).to_have_count(2)
        self.assertNotIn('Mouse', ' '.join(self.options.all_inner_texts()))  # other type


class ExpenseCategoryKeyboardTest(CategoryKeyboardMixin, UITestCase):
    kind, path, next_selector = 'expense', '/register/expense', '#id_payment_method'


class IncomeCategoryKeyboardTest(CategoryKeyboardMixin, UITestCase):
    kind, path, next_selector = 'income', '/register/income', 'button[type=submit]'
