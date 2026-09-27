from reports.repository.recurring_expense_repository import RecurringExpenseRepository
from decimal import Decimal
from django.utils.translation import gettext as _


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

    def get_fixed_expenses_summary(self, user, month, year):
        """
        Get a summary of fixed expenses including total amount, count, and
        payment status for the given month.

        Args:
            user: User instance
            month: Month number (1-12)
            year: Year (e.g., 2026)

        Returns:
            dict: Summary with total amount, count, formatted total, and
                pending/paid/not-generated counts for the given month
        """
        total_amount = self.repository.get_total_recurring_expenses_with_debit(user)
        month_status = self.repository.get_month_expenses_with_status(user, month, year)

        pending_count = sum(1 for entry in month_status if entry['status'] == 'pending')
        paid_count = sum(1 for entry in month_status if entry['status'] == 'paid')
        not_generated_count = sum(1 for entry in month_status if entry['status'] == 'not_generated')

        return {
            'total_amount': total_amount,
            'count': len(month_status),
            'formatted_total': self._format_currency(total_amount),
            'pending_count': pending_count,
            'paid_count': paid_count,
            'not_generated_count': not_generated_count,
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

    def toggle_paid(self, expense_id, user):
        """
        Alterna o status de pagamento de uma despesa gerada por despesa fixa.

        Args:
            expense_id: ID of the Expense
            user: User instance (ownership scope)

        Returns:
            Expense: Updated expense instance
        """
        return self.repository.toggle_paid(expense_id, user)

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

    def process_recurring_expenses_for_month(self, user, month, year):
        """
        Process recurring expenses for a specific month and year.
        Creates Expense records for all active recurring expenses.

        Args:
            user: User instance
            month: Month number (1-12)
            year: Year (e.g., 2026)

        Returns:
            dict: Results with created_count, skipped_count, errors
        """
        import datetime
        from registers.models import Expense, RecurringExpense

        # Validate inputs
        if not (1 <= month <= 12):
            return {
                'success': False,
                'error': _('Month must be between 1 and 12'),
                'created_count': 0,
                'skipped_count': 0,
                'errors': []
            }

        if not (2000 <= year <= 2100):
            return {
                'success': False,
                'error': _('Invalid year'),
                'created_count': 0,
                'skipped_count': 0,
                'errors': []
            }

        # Get all active recurring expenses for user
        recurring_expenses = RecurringExpense.objects.filter(
            user=user,
            generate_debit=True
        )

        created_count = 0
        skipped_count = 0
        errors = []
        created_expenses = []

        for recurring_expense in recurring_expenses:
            try:
                # Create expense date using day from start_date and provided month/year
                expense_date = datetime.date(
                    year, month, recurring_expense.start_date.day
                )
            except ValueError as e:
                # Invalid date (e.g., February 30)
                errors.append(_("%(description)s: invalid date - %(error)s") % {
                    'description': recurring_expense.description,
                    'error': str(e),
                })
                continue

            # Check if expense already exists
            existing = Expense.objects.filter(
                reccurring_expense=recurring_expense,
                date=expense_date
            ).exists()

            if existing:
                skipped_count += 1
                continue

            # Create new expense
            expense = Expense.objects.create(
                user=user,
                description=recurring_expense.description,
                amount=recurring_expense.total_amount,
                date=expense_date,
                category=recurring_expense.category,
                payment_method=recurring_expense.payment_method,
                reccurring_expense=recurring_expense,
                is_paid=False
            )

            created_count += 1
            created_expenses.append({
                'description': expense.description,
                'amount': expense.amount,
                'date': expense_date.strftime('%d/%m/%Y')
            })

        return {
            'success': True,
            'created_count': created_count,
            'skipped_count': skipped_count,
            'errors': errors,
            'created_expenses': created_expenses
        }
