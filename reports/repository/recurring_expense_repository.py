from registers.models import RecurringExpense
from django.db.models import Sum


class RecurringExpenseRepository:
    """
    Repository for RecurringExpense model following SOLID principles.
    Handles data access and query optimization for recurring expenses.
    """

    def get_total_recurring_expenses_with_debit(self):
        """
        Calculate the total amount of recurring expenses that have generate_debit=True.

        Returns:
            Decimal: Total amount of active recurring expenses
        """
        return (
            RecurringExpense.objects
            .filter(generate_debit=True)
            .aggregate(total=Sum('total_amount'))['total'] or 0
        )

    def get_active_recurring_expenses(self):
        """
        Get all active recurring expenses (generate_debit=True) with optimized query.

        Returns:
            QuerySet: Optimized queryset with related objects
        """
        return (
            RecurringExpense.objects
            .filter(generate_debit=True)
            .select_related('category', 'payment_method', 'user')
            .order_by('description')
        )

    def get_recurring_expenses_by_user(self, user):
        """
        Get recurring expenses for a specific user.

        Args:
            user: User instance

        Returns:
            QuerySet: User's recurring expenses with related objects
        """
        return (
            RecurringExpense.objects
            .filter(user=user, generate_debit=True)
            .select_related('category', 'payment_method')
            .order_by('description')
        )

    def get_recurring_expense_count(self):
        """
        Get count of active recurring expenses.

        Returns:
            int: Number of active recurring expenses
        """
        return RecurringExpense.objects.filter(generate_debit=True).count()