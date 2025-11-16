"""
Tests for CSV Record Creation Strategies

These tests verify the SOLID implementation of the strategy pattern
for creating different types of financial records from CSV data.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

from registers.models import Expense, Income, Category, PaymentMethod
from registers.services.csv_record_strategies import (
    NegativeAmountExpenseStrategy,
    PositiveAmountIncomeStrategy,
    ExplicitTypeStrategy,
    RecordStrategyFactory
)


class NegativeAmountExpenseStrategyTest(TestCase):
    """Test cases for NegativeAmountExpenseStrategy"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.strategy = NegativeAmountExpenseStrategy()

    def test_can_handle_negative_amount(self):
        """Strategy should handle rows with negative amounts"""
        row_data = {'amount': -100.50}
        self.assertTrue(self.strategy.can_handle(row_data))

    def test_cannot_handle_positive_amount(self):
        """Strategy should not handle rows with positive amounts"""
        row_data = {'amount': 100.50}
        self.assertFalse(self.strategy.can_handle(row_data))

    def test_cannot_handle_zero_amount(self):
        """Strategy should not handle rows with zero amount"""
        row_data = {'amount': 0}
        self.assertFalse(self.strategy.can_handle(row_data))

    def test_create_expense_from_negative_amount(self):
        """Should create expense with positive amount from negative CSV value"""
        row_data = {
            'amount': -50.75,
            'description': 'Test Expense',
            'date': date(2025, 10, 15),
            'category': 'Food',
            'payment_method': 'Credit Card'
        }

        record, error = self.strategy.create_record(
            user=self.user,
            row_data=row_data,
            auto_create_categories=True,
            auto_create_payment_methods=True
        )

        self.assertIsNone(error)
        self.assertIsInstance(record, Expense)
        self.assertEqual(record.amount, Decimal('50.75'))  # Should be positive
        self.assertEqual(record.description, 'Test Expense')
        self.assertEqual(record.user, self.user)

    def test_create_expense_auto_creates_category(self):
        """Should auto-create expense category if it doesn't exist"""
        row_data = {
            'amount': -25.00,
            'description': 'New Category Test',
            'date': date(2025, 10, 15),
            'category': 'New Category',
            'payment_method': 'Cash'
        }

        record, error = self.strategy.create_record(
            user=self.user,
            row_data=row_data,
            auto_create_categories=True,
            auto_create_payment_methods=True
        )

        self.assertIsNone(error)
        self.assertIsInstance(record, Expense)

        # Verify category was created with correct type
        category = Category.objects.get(name='New Category')
        self.assertEqual(category.type, 'expense')

    def test_create_expense_fails_without_auto_create_category(self):
        """Should fail if category doesn't exist and auto-create is disabled"""
        row_data = {
            'amount': -25.00,
            'description': 'Test',
            'date': date(2025, 10, 15),
            'category': 'Nonexistent Category',
            'payment_method': 'Cash'
        }

        record, error = self.strategy.create_record(
            user=self.user,
            row_data=row_data,
            auto_create_categories=False,
            auto_create_payment_methods=True
        )

        self.assertIsNotNone(error)
        self.assertIsNone(record)
        self.assertIn('not found', error)


class PositiveAmountIncomeStrategyTest(TestCase):
    """Test cases for PositiveAmountIncomeStrategy"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.strategy = PositiveAmountIncomeStrategy()

    def test_can_handle_positive_amount(self):
        """Strategy should handle rows with positive amounts"""
        row_data = {'amount': 1000.00}
        self.assertTrue(self.strategy.can_handle(row_data))

    def test_cannot_handle_negative_amount(self):
        """Strategy should not handle rows with negative amounts"""
        row_data = {'amount': -1000.00}
        self.assertFalse(self.strategy.can_handle(row_data))

    def test_create_income_from_positive_amount(self):
        """Should create income from positive CSV value"""
        row_data = {
            'amount': 3500.00,
            'description': 'Salary',
            'date': date(2025, 10, 1),
            'category': 'Salary'
        }

        record, error = self.strategy.create_record(
            user=self.user,
            row_data=row_data,
            auto_create_categories=True
        )

        self.assertIsNone(error)
        self.assertIsInstance(record, Income)
        self.assertEqual(record.amount, Decimal('3500.00'))
        self.assertEqual(record.description, 'Salary')
        self.assertEqual(record.user, self.user)

    def test_create_income_auto_creates_category(self):
        """Should auto-create income category if it doesn't exist"""
        row_data = {
            'amount': 500.00,
            'description': 'Freelance Work',
            'date': date(2025, 10, 15),
            'category': 'Freelance'
        }

        record, error = self.strategy.create_record(
            user=self.user,
            row_data=row_data,
            auto_create_categories=True
        )

        self.assertIsNone(error)
        self.assertIsInstance(record, Income)

        # Verify category was created with correct type
        category = Category.objects.get(name='Freelance')
        self.assertEqual(category.type, 'income')


class ExplicitTypeStrategyTest(TestCase):
    """Test cases for ExplicitTypeStrategy"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.strategy = ExplicitTypeStrategy()

    def test_can_handle_explicit_expense_type(self):
        """Strategy should handle rows with explicit 'expense' type"""
        row_data = {'type': 'expense', 'amount': 100}
        self.assertTrue(self.strategy.can_handle(row_data))

    def test_can_handle_explicit_income_type(self):
        """Strategy should handle rows with explicit 'income' type"""
        row_data = {'type': 'income', 'amount': 100}
        self.assertTrue(self.strategy.can_handle(row_data))

    def test_cannot_handle_missing_type(self):
        """Strategy should not handle rows without type field"""
        row_data = {'amount': 100}
        self.assertFalse(self.strategy.can_handle(row_data))

    def test_create_expense_with_explicit_type(self):
        """Should create expense when type='expense', regardless of amount sign"""
        row_data = {
            'type': 'expense',
            'amount': 75.00,  # Positive, but type says expense
            'description': 'Explicit Expense',
            'date': date(2025, 10, 15),
            'category': 'Shopping',
            'payment_method': 'Debit Card'
        }

        record, error = self.strategy.create_record(
            user=self.user,
            row_data=row_data,
            auto_create_categories=True,
            auto_create_payment_methods=True
        )

        self.assertIsNone(error)
        self.assertIsInstance(record, Expense)
        self.assertEqual(record.amount, Decimal('75.00'))

    def test_create_income_with_explicit_type(self):
        """Should create income when type='income', regardless of amount sign"""
        row_data = {
            'type': 'income',
            'amount': -200.00,  # Negative, but type says income
            'description': 'Explicit Income',
            'date': date(2025, 10, 15),
            'category': 'Bonus'
        }

        record, error = self.strategy.create_record(
            user=self.user,
            row_data=row_data,
            auto_create_categories=True
        )

        self.assertIsNone(error)
        self.assertIsInstance(record, Income)
        self.assertEqual(record.amount, Decimal('200.00'))  # Should use absolute value


class RecordStrategyFactoryTest(TestCase):
    """Test cases for RecordStrategyFactory"""

    def setUp(self):
        self.factory = RecordStrategyFactory()

    def test_get_strategy_for_explicit_type_takes_precedence(self):
        """Explicit type should take precedence over amount sign"""
        row_data = {
            'type': 'income',
            'amount': -100  # Negative, but type says income
        }

        strategy = self.factory.get_strategy(row_data)
        self.assertIsInstance(strategy, ExplicitTypeStrategy)

    def test_get_strategy_for_negative_amount(self):
        """Should return expense strategy for negative amounts without explicit type"""
        row_data = {'amount': -50.00}

        strategy = self.factory.get_strategy(row_data)
        self.assertIsInstance(strategy, NegativeAmountExpenseStrategy)

    def test_get_strategy_for_positive_amount(self):
        """Should return income strategy for positive amounts without explicit type"""
        row_data = {'amount': 1000.00}

        strategy = self.factory.get_strategy(row_data)
        self.assertIsInstance(strategy, PositiveAmountIncomeStrategy)

    def test_get_strategy_returns_none_for_zero_amount(self):
        """Should return None for zero amounts without explicit type"""
        row_data = {'amount': 0}

        strategy = self.factory.get_strategy(row_data)
        self.assertIsNone(strategy)

    def test_get_strategy_returns_none_for_invalid_amount(self):
        """Should return None for invalid amounts"""
        row_data = {'amount': 'invalid'}

        strategy = self.factory.get_strategy(row_data)
        self.assertIsNone(strategy)


class IntegrationTest(TestCase):
    """Integration tests for the complete strategy pattern flow"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.factory = RecordStrategyFactory()

    def test_mixed_csv_data_creates_correct_record_types(self):
        """Test importing mixed expenses and incomes in single CSV"""
        csv_rows = [
            {
                'amount': -50.00,
                'description': 'Grocery Shopping',
                'date': date(2025, 10, 1),
                'category': 'Food',
                'payment_method': 'Credit Card'
            },
            {
                'amount': 3000.00,
                'description': 'Monthly Salary',
                'date': date(2025, 10, 1),
                'category': 'Salary'
            },
            {
                'amount': -25.00,
                'description': 'Coffee',
                'date': date(2025, 10, 2),
                'category': 'Food',
                'payment_method': 'Cash'
            },
            {
                'type': 'income',
                'amount': 500.00,
                'description': 'Freelance Project',
                'date': date(2025, 10, 5),
                'category': 'Freelance'
            }
        ]

        expense_count = 0
        income_count = 0

        for row_data in csv_rows:
            strategy = self.factory.get_strategy(row_data)
            self.assertIsNotNone(strategy)

            record, error = strategy.create_record(
                user=self.user,
                row_data=row_data,
                auto_create_categories=True,
                auto_create_payment_methods=True
            )

            self.assertIsNone(error)
            self.assertIsNotNone(record)

            if isinstance(record, Expense):
                expense_count += 1
            elif isinstance(record, Income):
                income_count += 1

        self.assertEqual(expense_count, 2)
        self.assertEqual(income_count, 2)
        self.assertEqual(Expense.objects.count(), 2)
        self.assertEqual(Income.objects.count(), 2)
