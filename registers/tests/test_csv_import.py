"""
CSV import: each row becomes an Expense or an Income (by its `type` column, else by the amount's sign),
stored with the absolute amount.
"""

import io
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from registers.csv.importer import import_rows, read_csv
from registers.models import Category, Expense, Income


class ImportRowsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')

    def run_import(self, csv_text, **options):
        df, problems = read_csv(io.StringIO(csv_text))
        self.assertIsNotNone(df, problems)
        return import_rows(df, self.user, **options)

    def test_sign_decides_type_and_amounts_are_stored_positive(self):
        result = self.run_import("""date,description,amount,category,payment_method
2025-10-01,Monthly Salary,3500.00,Salary,
2025-10-02,Grocery Shopping,-150.50,Food,Credit Card
2025-10-05,Bonus,500.00,Bonus,
2025-10-06,Restaurant,-45.00,Dining,Cash""")

        self.assertEqual(result['stats'], {'total_rows': 4, 'imported': 4, 'imported_expenses': 2,
                                           'imported_incomes': 2, 'errors': 0})
        grocery = Expense.objects.get(description='Grocery Shopping')
        self.assertEqual(grocery.amount, Decimal('150.50'))
        self.assertEqual((grocery.user, grocery.payment_method.name), (self.user, 'Credit Card'))
        self.assertEqual(Income.objects.get(description='Monthly Salary').amount, Decimal('3500.00'))
        self.assertEqual(set(Income.objects.values_list('user', flat=True)), {self.user.id})

    def test_type_column_wins_over_sign_and_blank_type_falls_back_to_sign(self):
        result = self.run_import("""date,description,amount,category,type,payment_method
2025-10-01,Refund,-50.00,Refund,income,
2025-10-02,Purchase,75.00,Shopping,expense,Credit Card
2025-10-03,Coffee,-5.50,Dining,,Cash
2025-10-04,Gift,20.00,Gifts,,""")

        self.assertEqual(result['errors'], [])
        self.assertEqual(Income.objects.get(description='Refund').amount, Decimal('50.00'))
        self.assertEqual(Expense.objects.get(description='Purchase').amount, Decimal('75.00'))
        self.assertTrue(Expense.objects.filter(description='Coffee').exists())
        self.assertTrue(Income.objects.filter(description='Gift').exists())

    def test_auto_created_categories_take_the_record_type(self):
        self.run_import("""date,description,amount,category,payment_method
2025-10-01,Income from Other,100.00,Other,
2025-10-02,Expense for Other,-50.00,Other,Cash""")

        self.assertEqual(sorted(Category.objects.filter(name='Other').values_list('type', flat=True)),
                         ['expense', 'income'])
        self.assertEqual(Income.objects.get().category.type, 'income')
        self.assertEqual(Expense.objects.get().category.type, 'expense')

    def test_unknown_category_without_auto_create_is_a_row_error(self):
        result = self.run_import("""date,description,amount,category,payment_method
2025-10-15,Test,-25.00,Nonexistent Category,Cash""", auto_create_categories=False)

        self.assertEqual((result['stats']['imported'], result['stats']['errors']), (0, 1))
        self.assertEqual(len(result['errors']), 1)
        self.assertFalse(Expense.objects.exists())
        self.assertFalse(Category.objects.exists())

    def test_zero_amount_is_a_row_error(self):
        result = self.run_import("""date,description,amount,category
2025-10-01,Zero Amount,0.00,Other""")

        self.assertEqual((result['stats']['imported'], result['stats']['errors']), (0, 1))
        self.assertEqual(len(result['errors']), 1)
        self.assertFalse(Expense.objects.exists() or Income.objects.exists())

    def test_invalid_amount_is_warned_and_only_that_row_fails(self):
        csv_text = """date,description,amount,category,payment_method
2025-10-01,Salary,3500.00,Salary,
2025-10-02,Groceries,-120.50,Food,Credit Card
2025-10-03,Invalid,invalid_amount,Other,
2025-10-04,Bonus,500.00,Bonus,
2025-10-05,Restaurant,-45.00,Dining,Cash"""
        _, warnings = read_csv(io.StringIO(csv_text))
        self.assertEqual(len(warnings), 1)

        result = self.run_import(csv_text)

        self.assertEqual(result['stats'], {'total_rows': 5, 'imported': 4, 'imported_expenses': 2,
                                           'imported_incomes': 2, 'errors': 1})
        self.assertFalse(Expense.objects.filter(description='Invalid').exists())


    def test_a_file_with_only_blank_rows_is_empty(self):
        df, problems = read_csv(io.StringIO('date,description,amount\n,,\n,,\n'))
        self.assertIsNone(df)
        self.assertEqual(len(problems), 1)

    def test_the_first_data_row_is_imported(self):
        result = self.run_import('date,description,amount,type\n2025-10-01,Only row,10,expense\n')
        self.assertEqual(result['stats']['imported'], 1)
        self.assertTrue(Expense.objects.filter(description='Only row').exists())

class CsvImportViewTest(TestCase):
    CSV = """date,description,amount,category,payment_method
2025-10-01,Salary,3500.00,Salary,
2025-10-02,Groceries,-120.50,Food,Credit Card"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.force_login(self.user)

    def post(self, **options):
        return self.client.post(reverse('csv_import'), {
            'csv_text': self.CSV, 'separator': ',',
            'auto_create_categories': 'on', 'auto_create_payment_methods': 'on', **options,
        })

    def assert_imported_for_user(self):
        self.assertEqual(Expense.objects.get().user, self.user)
        self.assertEqual(Expense.objects.get().amount, Decimal('120.50'))
        self.assertEqual(Income.objects.get().user, self.user)

    def test_import_without_preview(self):
        response = self.post()

        self.assertRedirects(response, reverse('csv_import'))
        self.assert_imported_for_user()

    def test_preview_then_confirm_imports_the_previewed_rows(self):
        response = self.post(preview_mode='on')

        self.assertContains(response, 'Groceries')  # the rows are shown for review
        self.assertFalse(Expense.objects.exists() or Income.objects.exists())

        response = self.client.post(reverse('csv_import_confirm'))

        self.assertRedirects(response, reverse('csv_import'))
        self.assert_imported_for_user()

    def test_confirm_without_preview_imports_nothing(self):
        response = self.client.post(reverse('csv_import_confirm'))

        self.assertRedirects(response, reverse('csv_import'))
        self.assertFalse(Expense.objects.exists() or Income.objects.exists())
