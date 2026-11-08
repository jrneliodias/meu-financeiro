import os

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

# Playwright's sync API runs an event loop; Django's ORM guards against that.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


class UITestCase(StaticLiveServerTestCase):
    """Live server + headless Chromium. Skipped when Playwright is missing."""

    viewport = {'width': 1280, 'height': 800}

    @classmethod
    def setUpClass(cls):
        if sync_playwright is None:
            from unittest import SkipTest
            raise SkipTest('playwright is not installed')
        super().setUpClass()
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        if sync_playwright is not None:
            cls._browser.close()
            cls._pw.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.context = self._browser.new_context(viewport=self.viewport)
        self.page = self.context.new_page()
        self.page.set_default_timeout(5000)

    def tearDown(self):
        self.context.close()
        super().tearDown()

    def url(self, path):
        return f'{self.live_server_url}{path}'

    def login(self, user, password='pw12345!'):
        self.page.goto(self.url('/login/'))
        self.page.fill('input[name=username]', user.username)
        self.page.fill('input[name=password]', password)
        self.page.click('button[type=submit]')
        self.page.wait_for_url(lambda u: '/login' not in u)
