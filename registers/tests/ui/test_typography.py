from django.contrib.auth.models import User

from .base import UITestCase


class TypographyMixin:
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='ty', password='pw12345!')
        self.login(self.user)

    def style(self, selector, prop):
        return self.page.evaluate(
            '([s, p]) => getComputedStyle(document.querySelector(s))[p]', [selector, prop])

    def px(self, selector, prop='fontSize'):
        return float(self.style(selector, prop).replace('px', ''))


class InterFontTest(TypographyMixin, UITestCase):
    def test_body_uses_inter_with_tabular_digits(self):
        self.page.goto(self.url('/'))
        self.assertTrue(self.style('body', 'fontFamily').startswith('Inter'))
        self.assertIn('tabular-nums', self.style('body', 'fontVariantNumeric'))
        loaded = self.page.evaluate("document.fonts.load('14px Inter').then(f => f.length)")
        self.assertGreater(loaded, 0)


class DesktopScaleTest(TypographyMixin, UITestCase):
    viewport = {'width': 1280, 'height': 800}

    def test_desktop_scale_matches_reference(self):
        self.page.goto(self.url('/register/expense'))
        self.assertEqual(self.px('body'), 14)
        self.assertEqual(self.px('h1.text-2xl'), 28)
        self.assertEqual(self.px('#sidebar a'), 14)

    def test_title_and_subtitle_sizes(self):
        self.page.goto(self.url('/register/expense'))
        self.page.evaluate("""() => { for (const c of ['text-xl', 'text-lg']) {
            const e = document.createElement('p'); e.className = c + ' probe-' + c; e.textContent = 'x';
            document.body.appendChild(e); } }""")
        self.assertEqual(self.px('.probe-text-xl'), 20)
        self.assertEqual(self.px('.probe-text-lg'), 16)

    def test_login_uses_same_scale(self):
        self.page.context.clear_cookies()
        self.page.goto(self.url('/login/'))
        self.assertEqual(self.px('body'), 14)


class MobileScaleTest(TypographyMixin, UITestCase):
    viewport = {'width': 390, 'height': 800}

    def test_mobile_scale_is_smaller_but_inputs_stay_16px(self):
        self.page.goto(self.url('/register/expense'))
        body = self.px('body')
        self.assertTrue(12 <= body < 14, body)
        self.assertEqual(self.px('#id_description'), 16)
