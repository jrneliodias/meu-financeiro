import calendar
from datetime import date
from decimal import Decimal

from django.utils.timezone import localdate

from reports.repository.recurring_payment_repository import RecurringPaymentRepository


class RecurringPaymentService:
    """Build a monthly payment overview independently of the presentation."""

    def __init__(self, repository=None):
        self.repository = repository or RecurringPaymentRepository()

    def get_overview(self, user, month, year, today=None):
        if not 1 <= month <= 12 or not 2000 <= year <= 2100:
            raise ValueError('Invalid month or year')
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        occurrences = self.repository.get_occurrences(user, start, end)
        today = today or localdate()
        for expense in occurrences:
            expense.due_status = (
                'paid' if expense.is_paid else
                'overdue' if expense.date < today else
                'today' if expense.date == today else 'upcoming'
            )
        pending = sorted(
            (expense for expense in occurrences if not expense.is_paid),
            key=lambda expense: (expense.date, expense.description, expense.id),
        )
        paid = sorted(
            (expense for expense in occurrences if expense.is_paid),
            key=lambda expense: (expense.paid_at or date.min, expense.id), reverse=True,
        )
        missing = self.repository.get_missing_schedules(
            user, end, {expense.reccurring_expense_id for expense in occurrences},
        )
        return {
            'pending_expenses': pending,
            'paid_expenses': paid,
            'missing_schedules': missing,
            'pending_count': len(pending),
            'paid_count': len(paid),
            'missing_count': len(missing),
            'pending_total': sum((expense.amount for expense in pending), Decimal('0')),
            'paid_total': sum((expense.amount for expense in paid), Decimal('0')),
        }
