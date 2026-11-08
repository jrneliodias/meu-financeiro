from django.contrib.auth.models import User

from .base import UITestCase


class SmokeTest(UITestCase):
    def test_login_reaches_dashboard(self):
        user = User.objects.create_user(username='ui', password='pw12345!')
        self.login(user)
        self.assertNotIn('/login', self.page.url)
        self.assertIn('Meu Financeiro', self.page.content())
