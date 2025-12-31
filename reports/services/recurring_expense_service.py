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

    def create_recurring_expense(self, user, recurring_expense_data):
        """
        Cria uma nova despesa fixa.

        Args:
            user: User instance
            recurring_expense_data: Dictionary with form cleaned_data

        Returns:
            RecurringExpense: Created recurring expense instance
        """
        from registers.models import RecurringExpense
        recurring_expense = RecurringExpense(
            user=user,
            description=recurring_expense_data['description'],
            total_amount=recurring_expense_data['total_amount'],
            start_date=recurring_expense_data['start_date'],
            category=recurring_expense_data.get('category'),
            payment_method=recurring_expense_data.get('payment_method'),
            generate_debit=recurring_expense_data.get('generate_debit', True)
        )
        recurring_expense.save()
        return recurring_expense

    def update_recurring_expense(self, recurring_expense_id, recurring_expense_data):
        """
        Atualiza despesa fixa existente.

        Args:
            recurring_expense_id: ID of the recurring expense
            recurring_expense_data: Dictionary with form cleaned_data

        Returns:
            RecurringExpense: Updated recurring expense instance
        """
        recurring_expense = self.repository.get_recurring_expense_by_id(recurring_expense_id)
        recurring_expense.description = recurring_expense_data['description']
        recurring_expense.total_amount = recurring_expense_data['total_amount']
        recurring_expense.start_date = recurring_expense_data['start_date']
        recurring_expense.category = recurring_expense_data.get('category')
        recurring_expense.payment_method = recurring_expense_data.get('payment_method')
        recurring_expense.generate_debit = recurring_expense_data.get('generate_debit', True)
        recurring_expense.save()
        return recurring_expense

    def delete_recurring_expense(self, recurring_expense_id):
        """
        Exclui uma despesa fixa.

        Args:
            recurring_expense_id: ID of the recurring expense
        """
        recurring_expense = self.repository.get_recurring_expense_by_id(recurring_expense_id)
        recurring_expense.delete()

    def toggle_generate_debit(self, recurring_expense_id):
        """
        Ativa/desativa despesa fixa via repository.

        Args:
            recurring_expense_id: ID of the recurring expense

        Returns:
            RecurringExpense: Updated recurring expense instance
        """
        return self.repository.toggle_generate_debit(recurring_expense_id)

    def get_recurring_expense_with_expenses(self, recurring_expense_id):
        """
        Busca despesa fixa com todas as despesas geradas.

        Args:
            recurring_expense_id: ID of the recurring expense

        Returns:
            dict: Dictionary with recurring_expense, expenses, expense_count, total_generated
        """
        recurring_expense = self.repository.get_recurring_expense_by_id(recurring_expense_id)
        expenses = self.repository.get_expenses_by_recurring_expense(recurring_expense_id)
        return {
            'recurring_expense': recurring_expense,
            'expenses': expenses,
            'expense_count': expenses.count(),
            'total_generated': sum(expense.amount for expense in expenses)
        }