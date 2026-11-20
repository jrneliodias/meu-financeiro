from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils.timezone import localdate

from registers.models import Expense, RecurringExpense


def month_overview(user, year, month, today=None):
    """This month's occurrences of active recurring expenses, split by payment status,
    plus the active schedules that have no occurrence yet."""
    today = today or localdate()
    occurrences = list(
        Expense.objects.filter(user=user, reccurring_expense__user=user, reccurring_expense__generate_debit=True)
        .in_month(year, month)
        .select_related('category', 'payment_method').order_by('date', 'description', 'id')
    )
    for expense in occurrences:
        expense.due_status = (
            'paid' if expense.is_paid else
            'overdue' if expense.date < today else
            'today' if expense.date == today else 'upcoming'
        )
    pending = [expense for expense in occurrences if not expense.is_paid]
    paid = sorted((expense for expense in occurrences if expense.is_paid),
                  key=lambda expense: (expense.paid_at or date.min, expense.id), reverse=True)
    missing = list(
        RecurringExpense.objects.filter(user=user).due_in(year, month)
        .exclude(id__in={expense.reccurring_expense_id for expense in occurrences})
        .order_by('start_date', 'description')
    )
    return {
        'overdue_expenses': [expense for expense in pending if expense.due_status == 'overdue'],
        'today_expenses': [expense for expense in pending if expense.due_status == 'today'],
        'upcoming_expenses': [expense for expense in pending if expense.due_status == 'upcoming'],
        'next_expense': next((expense for expense in pending if expense.date >= today), None),
        'pending_expenses': pending,
        'paid_expenses': paid,
        'missing_schedules': missing,
        'pending_count': len(pending),
        'paid_count': len(paid),
        'missing_count': len(missing),
        'pending_total': sum((expense.amount for expense in pending), Decimal('0')),
        'paid_total': sum((expense.amount for expense in paid), Decimal('0')),
    }


def fixed_expenses_summary(user, year, month):
    return {
        'total_amount': RecurringExpense.objects.filter(user=user).due_in(year, month).charged_total(),
        'pending_count': month_overview(user, year, month)['pending_count'],
    }


def generate_month(user, year, month):
    """Create the month's expense for every recurring expense due that month that lacks one."""
    created, skipped = [], 0
    for recurring in RecurringExpense.objects.filter(user=user).due_in(year, month):
        expense, was_created = recurring.generate_for_month(year, month)
        if was_created:
            created.append(expense)
        else:
            skipped += 1
    return {'created_expenses': created, 'created_count': len(created), 'skipped_count': skipped}


def set_paid(user, expense_id, is_paid):
    """Persist the paid state of one of the user's recurring occurrences (Expense.DoesNotExist otherwise)."""
    with transaction.atomic():
        expense = Expense.objects.select_for_update().get(
            id=expense_id, user=user, reccurring_expense__isnull=False,
        )
        if expense.is_paid != is_paid:
            expense.is_paid = is_paid
            expense.paid_at = localdate() if is_paid else None
            expense.save(update_fields=['is_paid', 'paid_at', 'updated_at'])
        return expense
