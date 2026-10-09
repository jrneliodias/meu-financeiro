from registers.models import Expense, RecurringExpense


class RecurringPaymentRepository:
    """Read monthly occurrences, preserving bills from deactivated schedules."""

    def get_occurrences(self, user, start, end):
        return list(Expense.objects.filter(
            user=user, reccurring_expense__isnull=False,
            date__gte=start, date__lte=end,
        ).select_related('category', 'payment_method').order_by('date', 'description', 'id'))

    def get_missing_schedules(self, user, end, generated_ids):
        return list(RecurringExpense.objects.filter(
            user=user, generate_debit=True, start_date__lte=end,
        ).exclude(id__in=generated_ids).order_by('start_date', 'description'))
