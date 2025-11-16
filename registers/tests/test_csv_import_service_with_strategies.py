"""
Tests for CSVImportService with Strategy Pattern

These tests verify the integration of the strategy pattern
into the CSV import service.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date
import pandas as pd
import io

from registers.models import Expense, Income, Category, PaymentMethod
from registers.services.csv_import_service import CSVImportService


class CSVImportServiceWithStrategiesTest(TestCase):
    """Test CSV import service with expense/income strategy support"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.service = CSVImportService()

    def test_import_negative_amounts_as_expenses(self):
        """Negative amounts should be imported as expenses"""
        csv_data = """date,description,amount,category,payment_method
2025-10-01,Grocery Shopping,-150.50,Food,Credit Card
2025-10-02,Gas Station,-80.00,Transportation,Debit Card"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user)

        self.assertEqual(result['stats']['imported'], 2)
        self.assertEqual(result['stats']['imported_expenses'], 2)
        self.assertEqual(result['stats']['imported_incomes'], 0)
        self.assertEqual(Expense.objects.count(), 2)
        self.assertEqual(Income.objects.count(), 0)

        # Verify amounts are stored as positive values
        expense1 = Expense.objects.get(description='Grocery Shopping')
        self.assertEqual(float(expense1.amount), 150.50)

    def test_import_positive_amounts_as_incomes(self):
        """Positive amounts should be imported as incomes"""
        csv_data = """date,description,amount,category
2025-10-01,Monthly Salary,3500.00,Salary
2025-10-15,Freelance Project,800.00,Freelance"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user)

        self.assertEqual(result['stats']['imported'], 2)
        self.assertEqual(result['stats']['imported_expenses'], 0)
        self.assertEqual(result['stats']['imported_incomes'], 2)
        self.assertEqual(Expense.objects.count(), 0)
        self.assertEqual(Income.objects.count(), 2)

    def test_import_mixed_data(self):
        """Should correctly handle mixed expenses and incomes"""
        csv_data = """date,description,amount,category,payment_method
2025-10-01,Monthly Salary,3500.00,Salary,
2025-10-02,Grocery Shopping,-120.50,Food,Credit Card
2025-10-05,Bonus,500.00,Bonus,
2025-10-06,Restaurant,-45.00,Dining,Cash"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user)

        self.assertEqual(result['stats']['imported'], 4)
        self.assertEqual(result['stats']['imported_expenses'], 2)
        self.assertEqual(result['stats']['imported_incomes'], 2)
        self.assertEqual(Expense.objects.count(), 2)
        self.assertEqual(Income.objects.count(), 2)

    def test_import_with_explicit_type_column(self):
        """Explicit type column should take precedence over amount sign"""
        csv_data = """date,description,amount,category,type,payment_method
2025-10-01,Refund,50.00,Refund,income,
2025-10-02,Purchase,75.00,Shopping,expense,Credit Card"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user)

        self.assertEqual(result['stats']['imported'], 2)
        self.assertEqual(result['stats']['imported_expenses'], 1)
        self.assertEqual(result['stats']['imported_incomes'], 1)

        # Verify the explicit type was respected
        income = Income.objects.get(description='Refund')
        self.assertEqual(float(income.amount), 50.00)

        expense = Expense.objects.get(description='Purchase')
        self.assertEqual(float(expense.amount), 75.00)

    def test_import_creates_income_categories(self):
        """Should auto-create income categories with correct type"""
        csv_data = """date,description,amount,category
2025-10-01,Salary,3500.00,Monthly Salary
2025-10-15,Freelance,800.00,Freelance Work"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user, auto_create_categories=True)

        self.assertEqual(result['stats']['imported'], 2)

        # Verify categories were created with income type
        salary_cat = Category.objects.get(name='Monthly Salary')
        self.assertEqual(salary_cat.type, 'income')

        freelance_cat = Category.objects.get(name='Freelance Work')
        self.assertEqual(freelance_cat.type, 'income')

    def test_import_creates_expense_categories(self):
        """Should auto-create expense categories with correct type"""
        csv_data = """date,description,amount,category,payment_method
2025-10-01,Groceries,-120.50,Grocery Shopping,Credit Card
2025-10-02,Gas,-60.00,Transportation,Cash"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user, auto_create_categories=True)

        self.assertEqual(result['stats']['imported'], 2)

        # Verify categories were created with expense type
        grocery_cat = Category.objects.get(name='Grocery Shopping')
        self.assertEqual(grocery_cat.type, 'expense')

        transport_cat = Category.objects.get(name='Transportation')
        self.assertEqual(transport_cat.type, 'expense')

    def test_import_zero_amount_is_skipped(self):
        """Zero amounts should be skipped with appropriate error"""
        csv_data = """date,description,amount,category
2025-10-01,Zero Amount,0.00,Other"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user)

        self.assertEqual(result['stats']['imported'], 0)
        self.assertEqual(result['stats']['errors'], 1)
        self.assertIn('No strategy found', result['errors'][0])

    def test_import_statistics_accuracy(self):
        """Import statistics should accurately reflect imported records"""
        csv_data = """date,description,amount,category,payment_method
2025-10-01,Salary,3500.00,Salary,
2025-10-02,Groceries,-120.50,Food,Credit Card
2025-10-03,Invalid,invalid_amount,Other,
2025-10-04,Bonus,500.00,Bonus,
2025-10-05,Restaurant,-45.00,Dining,Cash"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user)

        # One row will have invalid amount (converted to NaN by pandas)
        # and will be caught by the "Missing required fields" check
        self.assertEqual(result['stats']['total_rows'], 5)
        self.assertEqual(result['stats']['imported'], 4)
        self.assertEqual(result['stats']['imported_expenses'], 2)
        self.assertEqual(result['stats']['imported_incomes'], 2)
        self.assertEqual(result['stats']['errors'], 1)

    def test_backward_compatibility_all_expenses(self):
        """Should maintain backward compatibility with old CSV format (all expenses)"""
        # Old format: no type column, all negative amounts
        csv_data = """date,description,amount,category,payment_method
2025-10-01,Grocery,-100.00,Food,Credit Card
2025-10-02,Gas,-50.00,Transportation,Debit Card
2025-10-03,Coffee,-5.50,Dining,Cash"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user)

        self.assertEqual(result['stats']['imported'], 3)
        self.assertEqual(result['stats']['imported_expenses'], 3)
        self.assertEqual(result['stats']['imported_incomes'], 0)
        self.assertEqual(Expense.objects.count(), 3)

    def test_category_type_mismatch_with_auto_create(self):
        """Should create separate categories for expense vs income with same name"""
        csv_data = """date,description,amount,category,payment_method
2025-10-01,Income from Other,100.00,Other,
2025-10-02,Expense for Other,-50.00,Other,Cash"""

        df, errors = self.service.parse_csv_file_from_string(csv_data, skip_header=False)
        self.assertIsNotNone(df)

        result = self.service.import_data(df, self.user, auto_create_categories=True)

        self.assertEqual(result['stats']['imported'], 2)

        # Should have two "Other" categories with different types
        other_categories = Category.objects.filter(name='Other')
        self.assertEqual(other_categories.count(), 2)

        expense_cat = Category.objects.get(name='Other', type='expense')
        income_cat = Category.objects.get(name='Other', type='income')

        self.assertIsNotNone(expense_cat)
        self.assertIsNotNone(income_cat)
