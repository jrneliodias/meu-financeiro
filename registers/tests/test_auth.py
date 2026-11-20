from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LogoutTest(TestCase):
    def test_the_sidebar_logout_signs_the_user_out(self):
        self.client.force_login(User.objects.create_user('demo', password='x'))
        page = self.client.get(reverse('register_income')).content.decode()
        self.assertIn(f'<form action="{reverse("logout")}" method="post">', page)

        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('register_income')).status_code, 302)
