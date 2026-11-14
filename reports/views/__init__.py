"""Views de reports, um módulo por assunto. urls.py usa `views.<nome>`."""
from .ajax import (  # noqa: F401
    category_expense_details_ajax, daily_spending_data_ajax,
    expense_details_ajax, installment_expenses_ajax,
)
from .dashboard import (  # noqa: F401
    categories, expense_report, expenses, installments, spending,
)
from .expense_update import ExpenseUpdateView  # noqa: F401
from .recurring import (  # noqa: F401
    RecurringExpenseUpdateView, payment_notifications, process_recurring_expenses_ajax,
    recurring_expense_delete, recurring_expense_expenses, recurring_expense_list,
    recurring_expense_set_paid, recurring_expense_toggle, recurring_expense_toggle_paid,
    recurring_payments,
)
