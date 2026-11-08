import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.models import Category


class CategoryAjaxTypeTest(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user(username='c'))
        Category.objects.create(name='Mercado', type='expense')
        Category.objects.create(name='Salario', type='income')

    def names(self, **params):
        r = self.client.get(reverse('category_search_ajax'), params)
        return [c['name'] for c in r.json()['categories']]

    def create(self, name, **extra):
        r = self.client.post(reverse('category_create_ajax'),
                             json.dumps({'name': name, **extra}), content_type='application/json')
        return r.json()['category']['id']

    def test_search_income_only_returns_income(self):
        self.assertEqual(self.names(type='income'), ['Salario'])

    def test_search_defaults_to_expense(self):
        self.assertEqual(self.names(), ['Mercado'])
        self.assertEqual(self.names(type='xyz'), ['Mercado'])

    def test_create_income_category(self):
        cat = Category.objects.get(pk=self.create('Bonus', type='income'))
        self.assertEqual(cat.type, 'income')

    def test_create_reuses_existing_of_same_type_only(self):
        income_id = Category.objects.get(name='Salario').pk
        self.assertEqual(self.create('salario', type='income'), income_id)
        self.assertNotEqual(self.create('salario'), income_id)  # expense: new category
        self.assertEqual(Category.objects.filter(name__iexact='salario').count(), 2)

    def test_create_invalid_type_falls_back_to_expense(self):
        cat = Category.objects.get(pk=self.create('Zzz', type='xyz'))
        self.assertEqual(cat.type, 'expense')
