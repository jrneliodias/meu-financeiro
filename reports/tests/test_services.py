from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from reports.services import ExpenseService
from registers.models import PaymentMethod, Expense, Category, Income
from reports.repository import ExpenseRepository, IncomeRepository


class ExpenseServiceTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Create test payment methods
        self.credit_card = PaymentMethod.objects.create(
            name='Credit Card',
            start_billing_day=15,
        )

        self.debit_card = PaymentMethod.objects.create(
            name='Debit Card',
            start_billing_day=1,
        )

        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
        )

        # Initialize repositories
        self.expense_repository = ExpenseRepository()
        self.income_repository = IncomeRepository()

        # Initialize service
        self.service = ExpenseService(
            expense_repository=self.expense_repository,
            income_repository=self.income_repository,
            year=2024
        )

    def test_calculate_end_date_regular_month(self):
        """Test end date calculation for a regular month"""
        # Test for billing day 15 in March
        end_date = self.service.calculate_end_date(15, 3, 2024)
        self.assertEqual(end_date, date(2024, 4, 14))

        # Test for billing day 1
        end_date = self.service.calculate_end_date(1, 3, 2024)
        self.assertEqual(end_date, date(2024, 3, 31))

    def test_calculate_end_date_december(self):
        """Test end date calculation for December"""
        # Test for billing day 15 in December
        end_date = self.service.calculate_end_date(15, 12, 2024)
        self.assertEqual(end_date, date(2025, 1, 14))

        # Test for billing day 1 in December
        end_date = self.service.calculate_end_date(1, 12, 2024)
        self.assertEqual(end_date, date(2024, 12, 31))

    def test_expense_calculation_december_january(self):
        """Test expense calculation spanning December-January"""
        # Create expenses for December 2024
        december_expense = Expense.objects.create(
            description='December Expense',
            amount=Decimal('100.00'),
            date=date(2024, 12, 20),
            category=self.category,
            payment_method=self.credit_card,
            user=self.user
        )

        # Create expense for January 2025
        january_expense = Expense.objects.create(
            description='January Expense',
            amount=Decimal('150.00'),
            date=date(2025, 1, 10),
            category=self.category,
            payment_method=self.credit_card,
            user=self.user
        )

        # Get monthly totals using year=2025 so January 2025 period (Dec 15 2024 - Jan 14 2025)
        # captures both expenses
        service_2025 = ExpenseService(
            expense_repository=self.expense_repository,
            income_repository=self.income_repository,
            year=2025
        )
        result = service_2025.calculate_monthly_payment_method_total_expense_datasets()

        # Since credit card billing cycle is 15th-14th,
        # both expenses should appear in January's total
        january_data = None
        for dataset in result['datasets']:
            if dataset['label'] == 'Credit Card':
                january_index = result['labels'].index('January')
                january_data = dataset['data'][january_index]
                break

        self.assertEqual(january_data, 250.0)  # 100 + 150

    def test_total_expenses_calculation(self):
        """Test total expenses calculation"""
        # Create multiple expenses
        expenses = [
            Expense.objects.create(
                description=f'Expense {i}',
                amount=Decimal('100.00'),
                date=date(2024, 3, i),
                category=self.category,
                payment_method=self.debit_card,
                user=self.user
            ) for i in range(1, 4)
        ]

        result = self.service.calculate_monthly_expenses_total()

        # Check March total
        march_index = result['labels'].index('March')
        march_total = result['datasets'][0]['datasets'][march_index]

        self.assertEqual(march_total, 300.0)  # 3 expenses of 100 each

    def test_income_calculation(self):
        """Test income calculation"""
        # Create test income
        Income.objects.create(
            description='March Salary',
            amount=Decimal('5000.00'),
            date=date(2024, 3, 5),
            user=self.user
        )

        result = self.service.calculate_total_incomes_by_month()

        # March should be index 2 (0-based index)
        self.assertEqual(result['datasets'][2], 5000.0)
