"""
CSV Record Creation Strategies

This module implements the Strategy Pattern (SOLID: Open/Closed Principle)
for determining and creating different types of financial records from CSV data.

Each strategy is responsible for:
- Determining if it can handle a specific row
- Creating the appropriate record type (Expense or Income)
- Validating and preparing data for that record type
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
import logging

from ..models import Expense, Income, Category, PaymentMethod

logger = logging.getLogger(__name__)


class RecordCreationStrategy(ABC):
    """
    Base strategy interface for creating financial records from CSV data.

    SOLID Principles:
    - Single Responsibility: Each strategy handles one type of record
    - Open/Closed: New record types can be added without modifying existing code
    - Liskov Substitution: All strategies can be used interchangeably
    - Interface Segregation: Minimal interface with only essential methods
    - Dependency Inversion: Depends on abstractions (Category, PaymentMethod models)
    """

    @abstractmethod
    def can_handle(self, row_data: Dict[str, Any]) -> bool:
        """
        Determine if this strategy can handle the given row data.

        Args:
            row_data: Dictionary containing CSV row data

        Returns:
            True if this strategy should handle the row, False otherwise
        """
        pass

    @abstractmethod
    def create_record(self, user: User, row_data: Dict[str, Any],
                     auto_create_categories: bool = True,
                     auto_create_payment_methods: bool = True) -> Tuple[Any, Optional[str]]:
        """
        Create a financial record from CSV row data.

        Args:
            user: User who owns the record
            row_data: Dictionary containing CSV row data
            auto_create_categories: Whether to auto-create missing categories
            auto_create_payment_methods: Whether to auto-create missing payment methods

        Returns:
            Tuple of (created_record, error_message)
            - created_record: The created model instance or None if failed
            - error_message: Error description or None if successful
        """
        pass

    def _get_or_create_category(self, category_name: str, category_type: str,
                               auto_create: bool) -> Tuple[Optional[Category], Optional[str]]:
        """
        Helper method to get or create a category.

        Args:
            category_name: Name of the category
            category_type: Type of category ('expense' or 'income')
            auto_create: Whether to auto-create if not found

        Returns:
            Tuple of (category, error_message)
        """
        category_name = category_name.strip()

        if auto_create:
            category, created = Category.objects.get_or_create(
                name=category_name,
                type=category_type,
                defaults={'name': category_name, 'type': category_type}
            )
            return category, None
        else:
            try:
                category = Category.objects.get(name=category_name, type=category_type)
                return category, None
            except Category.DoesNotExist:
                return None, _("Category '%(category)s' of type '%(type)s' not found") % {
                    'category': category_name,
                    'type': category_type,
                }

    def _get_or_create_payment_method(self, payment_method_name: str,
                                     auto_create: bool) -> Tuple[Optional[PaymentMethod], Optional[str]]:
        """
        Helper method to get or create a payment method.

        Args:
            payment_method_name: Name of the payment method
            auto_create: Whether to auto-create if not found

        Returns:
            Tuple of (payment_method, error_message)
        """
        payment_method_name = payment_method_name.strip()

        if auto_create:
            payment_method, created = PaymentMethod.objects.get_or_create(
                name=payment_method_name,
                defaults={'name': payment_method_name, 'start_billing_day': 1}
            )
            return payment_method, None
        else:
            try:
                payment_method = PaymentMethod.objects.get(name=payment_method_name)
                return payment_method, None
            except PaymentMethod.DoesNotExist:
                return None, _("Payment method '%(payment_method)s' not found") % {
                    'payment_method': payment_method_name
                }


class NegativeAmountExpenseStrategy(RecordCreationStrategy):
    """
    Strategy for creating Expense records from rows with negative amounts.

    This strategy interprets negative values as expenses (debits).
    The amount is stored as absolute value in the Expense model.
    """

    def can_handle(self, row_data: Dict[str, Any]) -> bool:
        """Handle rows with negative amounts as expenses."""
        amount = row_data.get('amount')
        if amount is None:
            return False

        # Convert to Decimal for accurate comparison
        try:
            amount_decimal = Decimal(str(amount))
            return amount_decimal < 0
        except (ValueError, TypeError, Exception):
            return False

    def create_record(self, user: User, row_data: Dict[str, Any],
                     auto_create_categories: bool = True,
                     auto_create_payment_methods: bool = True) -> Tuple[Any, Optional[str]]:
        """Create an Expense record from negative amount row."""
        try:
            # Get category
            category_name = str(row_data.get('category', 'Outros'))
            category, error = self._get_or_create_category(
                category_name, 'expense', auto_create_categories
            )
            if error:
                return None, error

            # Get payment method
            payment_method_name = str(row_data.get('payment_method', 'Crédito - Nubank'))
            payment_method, error = self._get_or_create_payment_method(
                payment_method_name, auto_create_payment_methods
            )
            if error:
                return None, error

            # Convert negative amount to positive for Expense model
            amount = abs(float(row_data['amount']))

            # Create expense
            expense = Expense(
                user=user,
                description=str(row_data['description']).strip(),
                amount=amount,
                date=row_data['date'].date() if hasattr(row_data['date'], 'date') else row_data['date'],
                category=category,
                payment_method=payment_method,
            )
            expense.save()

            logger.info(f"Created expense from negative amount: {expense.description} - {expense.amount}")
            return expense, None

        except Exception as e:
            error_msg = _("Error creating expense: %(error)s") % {'error': str(e)}
            logger.error(error_msg)
            return None, error_msg


class PositiveAmountIncomeStrategy(RecordCreationStrategy):
    """
    Strategy for creating Income records from rows with positive amounts.

    This strategy interprets positive values as income (credits).
    """

    def can_handle(self, row_data: Dict[str, Any]) -> bool:
        """Handle rows with positive amounts as income."""
        amount = row_data.get('amount')
        if amount is None:
            return False

        # Convert to Decimal for accurate comparison
        try:
            amount_decimal = Decimal(str(amount))
            return amount_decimal > 0
        except (ValueError, TypeError, Exception):
            return False

    def create_record(self, user: User, row_data: Dict[str, Any],
                     auto_create_categories: bool = True,
                     auto_create_payment_methods: bool = True) -> Tuple[Any, Optional[str]]:
        """Create an Income record from positive amount row."""
        try:
            # Get category
            category_name = str(row_data.get('category', 'Outros'))
            category, error = self._get_or_create_category(
                category_name, 'income', auto_create_categories
            )
            if error:
                return None, error

            # Income doesn't use payment methods
            amount = float(row_data['amount'])

            # Create income
            income = Income(
                user=user,
                description=str(row_data['description']).strip(),
                amount=amount,
                date=row_data['date'].date() if hasattr(row_data['date'], 'date') else row_data['date'],
                category=category,
            )
            income.save()

            logger.info(f"Created income from positive amount: {income.description} - {income.amount}")
            return income, None

        except Exception as e:
            error_msg = _("Error creating income: %(error)s") % {'error': str(e)}
            logger.error(error_msg)
            return None, error_msg


class ExplicitTypeStrategy(RecordCreationStrategy):
    """
    Strategy for creating records based on explicit 'type' column in CSV.

    This strategy checks for a 'type' column and creates the appropriate
    record type regardless of amount sign. This allows for maximum flexibility.

    Priority: This strategy should be checked first as explicit type
    specification takes precedence over amount-based inference.
    """

    def can_handle(self, row_data: Dict[str, Any]) -> bool:
        """Handle rows with explicit 'type' column."""
        record_type = row_data.get('type', '').lower().strip()
        return record_type in ['expense', 'income']

    def create_record(self, user: User, row_data: Dict[str, Any],
                     auto_create_categories: bool = True,
                     auto_create_payment_methods: bool = True) -> Tuple[Any, Optional[str]]:
        """Create record based on explicit type field."""
        record_type = row_data.get('type', '').lower().strip()

        if record_type == 'expense':
            return self._create_expense(user, row_data, auto_create_categories,
                                       auto_create_payment_methods)
        elif record_type == 'income':
            return self._create_income(user, row_data, auto_create_categories)
        else:
            return None, _("Invalid type: %(record_type)s") % {'record_type': record_type}

    def _create_expense(self, user: User, row_data: Dict[str, Any],
                       auto_create_categories: bool,
                       auto_create_payment_methods: bool) -> Tuple[Any, Optional[str]]:
        """Create expense record."""
        try:
            category_name = str(row_data.get('category', 'Outros'))
            category, error = self._get_or_create_category(
                category_name, 'expense', auto_create_categories
            )
            if error:
                return None, error

            payment_method_name = str(row_data.get('payment_method', 'Crédito - Nubank'))
            payment_method, error = self._get_or_create_payment_method(
                payment_method_name, auto_create_payment_methods
            )
            if error:
                return None, error

            # Use absolute value for expenses
            amount = abs(float(row_data['amount']))

            expense = Expense(
                user=user,
                description=str(row_data['description']).strip(),
                amount=amount,
                date=row_data['date'].date() if hasattr(row_data['date'], 'date') else row_data['date'],
                category=category,
                payment_method=payment_method,
            )
            expense.save()

            logger.info(f"Created expense from explicit type: {expense.description} - {expense.amount}")
            return expense, None

        except Exception as e:
            error_msg = _("Error creating expense: %(error)s") % {'error': str(e)}
            logger.error(error_msg)
            return None, error_msg

    def _create_income(self, user: User, row_data: Dict[str, Any],
                      auto_create_categories: bool) -> Tuple[Any, Optional[str]]:
        """Create income record."""
        try:
            category_name = str(row_data.get('category', 'Outros'))
            category, error = self._get_or_create_category(
                category_name, 'income', auto_create_categories
            )
            if error:
                return None, error

            # Use absolute value for incomes
            amount = abs(float(row_data['amount']))

            income = Income(
                user=user,
                description=str(row_data['description']).strip(),
                amount=amount,
                date=row_data['date'].date() if hasattr(row_data['date'], 'date') else row_data['date'],
                category=category,
            )
            income.save()

            logger.info(f"Created income from explicit type: {income.description} - {income.amount}")
            return income, None

        except Exception as e:
            error_msg = _("Error creating income: %(error)s") % {'error': str(e)}
            logger.error(error_msg)
            return None, error_msg


class RecordStrategyFactory:
    """
    Factory for selecting the appropriate record creation strategy.

    SOLID Principles:
    - Single Responsibility: Only responsible for strategy selection
    - Open/Closed: New strategies can be added without modification
    - Dependency Inversion: Depends on RecordCreationStrategy abstraction

    The factory tries strategies in order of priority:
    1. ExplicitTypeStrategy - explicit 'type' column takes precedence
    2. NegativeAmountExpenseStrategy - negative amounts = expenses
    3. PositiveAmountIncomeStrategy - positive amounts = income
    """

    def __init__(self):
        """Initialize factory with available strategies in priority order."""
        self.strategies = [
            ExplicitTypeStrategy(),
            NegativeAmountExpenseStrategy(),
            PositiveAmountIncomeStrategy(),
        ]

    def get_strategy(self, row_data: Dict[str, Any]) -> Optional[RecordCreationStrategy]:
        """
        Get the appropriate strategy for the given row data.

        Args:
            row_data: Dictionary containing CSV row data

        Returns:
            The first strategy that can handle the row, or None if no strategy matches
        """
        for strategy in self.strategies:
            if strategy.can_handle(row_data):
                return strategy
        return None

    def add_strategy(self, strategy: RecordCreationStrategy, priority: int = -1):
        """
        Add a new strategy to the factory.

        This allows extending functionality without modifying existing code.

        Args:
            strategy: The strategy to add
            priority: Position in the strategy list (default: append at end)
        """
        if priority < 0 or priority >= len(self.strategies):
            self.strategies.append(strategy)
        else:
            self.strategies.insert(priority, strategy)
