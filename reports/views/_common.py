"""Helpers e singletons compartilhados pelas views de reports."""
import calendar
from reports.repository import ExpenseRepository, IncomeRepository
from reports.services import BalanceService, BudgetEstimateService
from reports.services.installment_progress_calculator import InstallmentProgressCalculator
from reports.services.recurring_expense_service import RecurringExpenseService

expense_repository = ExpenseRepository()
income_repository = IncomeRepository()
installment_calculator = InstallmentProgressCalculator()
balance_service = BalanceService()
recurring_expense_service = RecurringExpenseService()
budget_estimate_service = BudgetEstimateService()


def get_selected_year_and_month(request, default_year, default_month):
    """Extracts selected year and month from the request or defaults to the current year and month."""
    selected_year = int(request.GET.get('year', default_year))
    selected_month = int(request.GET.get('month', default_month))
    selected_month_name = calendar.month_name[selected_month]

    return selected_year, selected_month, selected_month_name


def format_brl(value):
    """
    Formats a float value into Brazilian Real currency format (R$ 1.234,90).
    """
    # Ensure value has two decimal places and replace the decimal and thousand separators
    formatted_value = "R$ {:,.2f}".format(value).replace(
        ",", "X").replace(".", ",").replace("X", ".")
    return formatted_value
