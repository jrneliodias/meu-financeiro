"""Views de reports, um módulo por assunto. urls.py usa `views.<nome>`."""
from .ajax import daily_spending_data_ajax  # noqa: F401
from .dashboard import (  # noqa: F401
    budget_breakdown, categories, expense_report, expenses, installments, spending,
)
from .expense_list import expense_list_page  # noqa: F401
from .expense_update import ExpenseUpdateView  # noqa: F401
from .recurring import (  # noqa: F401
    RecurringExpenseUpdateView, payment_notifications, recurring_expense_process,
    recurring_expense_delete, recurring_expense_expenses, recurring_expense_list,
    recurring_expense_set_paid, recurring_expense_toggle, recurring_expense_toggle_paid,
    recurring_payments,
)
