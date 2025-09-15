from reports.repository.recurring_expense_repository import RecurringExpenseRepository
from decimal import Decimal


class RecurringExpenseService:
    """
    Service class for RecurringExpense business logic following SOLID principles.
    Handles calculation and processing of recurring expenses data.
    """

    def __init__(self, recurring_expense_repository=None):
        """
        Initialize service with dependency injection for better testability.

        Args:
            recurring_expense_repository: RecurringExpenseRepository instance
        """
        self.repository = recurring_expense_repository or RecurringExpenseRepository()

    def get_total_fixed_expenses(self):
        """
        Calculate the total amount of fixed expenses (recurring expenses with generate_debit=True).

        Returns:
            Decimal: Total amount of active recurring expenses
        """
        return self.repository.get_total_recurring_expenses_with_debit()

    def get_fixed_expenses_summary(self):
        """
        Get a summary of fixed expenses including total amount and count.

        Returns:
            dict: Summary with total amount, count, and formatted total
        """
        total_amount = self.get_total_fixed_expenses()
        count = self.repository.get_recurring_expense_count()

        return {
            'total_amount': total_amount,
            'count': count,
            'formatted_total': self._format_currency(total_amount)
        }

    def get_active_fixed_expenses_list(self):
        """
        Get list of all active recurring expenses with details.

        Returns:
            QuerySet: Active recurring expenses with related data
        """
        return self.repository.get_active_recurring_expenses()

    def get_user_fixed_expenses(self, user):
        """
        Get fixed expenses for a specific user.

        Args:
            user: User instance

        Returns:
            QuerySet: User's recurring expenses
        """
        return self.repository.get_recurring_expenses_by_user(user)

    def _format_currency(self, value):
        """
        Format value as Brazilian Real currency.

        Args:
            value: Decimal value to format

        Returns:
            str: Formatted currency string
        """
        if value is None:
            value = Decimal('0.00')

        # Ensure value has two decimal places and replace separators for Brazilian format
        formatted_value = "R$ {:,.2f}".format(float(value)).replace(
            ",", "X").replace(".", ",").replace("X", ".")
        return formatted_value