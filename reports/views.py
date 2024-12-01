from django.shortcuts import render
from django.db.models.functions import TruncMonth, TruncYear
from collections import defaultdict
import calendar
from datetime import datetime
from reports.repository import ExpenseRepository, IncomeRepository, CategoryRepository
from reports.services import ExpenseService
from django.views.generic import UpdateView
from registers.models import Expense
from registers.forms import ExpenseForm

expense_repository = ExpenseRepository()
income_repository = IncomeRepository()
category_repository = CategoryRepository()


def index(request):
    return render(request, 'core/index.html')


def expense_report(request):
    # Create an instance of ExpenseRepository

    # Get the current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Get distinct years and months
    distinct_years = expense_repository.get_distinct_years_in_tuples()
    distinct_months = expense_repository.get_distinct_months_in_tuples()

    # Get the selected year and month from the request
    selected_year, selected_month, selected_month_name = get_selected_year_and_month(
        request, current_year, current_month)

    expense_service = ExpenseService(
        expense_repository, income_repository, year=selected_year)

    # Get expenses grouped by month and category for the current year
    expenses_by_category_by_month, total_expense_by_month, total_expense_by_month_list = get_expenses_by_month_and_category(
        selected_year)

    # Get expenses for the selected month
    expenses_by_category = get_expenses_by_selected_month(
        selected_year, selected_month)

    # Get distinct category names
    categories = get_distinct_categories()

    # Get incomes by month
    incomes_by_month = get_incomes_by_month(selected_year)

    formatted_expenses = [
        total_expense_by_month_list.get(month_name, 'R$ 0,00') for _, month_name in distinct_months
    ]

    monthy_payment_method_expense_totals = expense_service.monthly_payment_method_expense_totals(
        current_year)

    calculated_monthy_payment_method_expense_totals = expense_service.calculate_monthly_payment_method_total_expense(
    )

    monthy_expense_total = expense_service.calculate_monthly_expenses_total()
    monthly_expense_income_datasets = expense_service.create_month_total_datasets()
    monthly_expenses_queryset = get_expenses_by_month(
        selected_year, selected_month
    )

    # Prepare the context
    context = {
        'expenses_by_category_by_month': expenses_by_category_by_month,
        'total_expense_by_month': total_expense_by_month,
        'total_expense_by_month_list': formatted_expenses,
        'incomes_by_month': incomes_by_month,
        'categories': categories,
        'current_year': current_year,
        'distinct_years': distinct_years,
        'distinct_months': distinct_months,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_month_name': selected_month_name,
        'expenses_by_category': expenses_by_category,
        'monthy_payment_method_expense_totals': monthy_payment_method_expense_totals,
        'calculated_monthy_payment_method_expense_totals': calculated_monthy_payment_method_expense_totals,
        'monthly_expense_income_datasets': monthly_expense_income_datasets,
        'monthly_expenses_queryset': monthly_expenses_queryset
    }

    return render(request, 'reports/expense_report.html', context)


class ExpenseUpdateView(UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'reports/expense_update.html'
    success_url = '/'


def get_expenses_by_month_and_category(year):
    """
    Returns expenses categorized by month and category for the given year.
    """
    expenses = expense_repository.get_expenses_for_year(year)
    months_in_database = expense_repository.get_months_in_list()

    expenses_by_category = build_expenses_by_category(expenses)
    total_expense_by_month = calculate_total_expense_by_month(expenses)

    fill_missing_months(expenses_by_category, months_in_database)

    return (
        sort_category_by_month(expenses_by_category),
        sort_by_month(total_expense_by_month),
        format_total_expenses(total_expense_by_month)
    )


def build_expenses_by_category(expenses):
    """Build a nested dictionary of expenses by category and month."""
    expenses_by_category = defaultdict(lambda: defaultdict(float))
    for expense in expenses:
        month = expense['month'].strftime('%B')
        category = expense['category__name']
        total = float(expense['total_amount'])
        expenses_by_category[category][month] = format_brl(total)
    return expenses_by_category


def calculate_total_expense_by_month(expenses):
    """Calculate the total expense for each month."""
    total_by_month = defaultdict(float)
    for expense in expenses:
        month = expense['month'].strftime('%B')
        total_by_month[month] += float(expense['total_amount'])
    return total_by_month


def fill_missing_months(expenses_by_category, months_in_database):
    """Fill missing months with 0.00 in each category."""
    for months in expenses_by_category.values():
        for month in months_in_database:
            if month not in months:
                months[month] = 0.00


def format_total_expenses(total_expense_by_month):
    """Format total expenses for each month."""
    return {month: format_brl(amount) for month, amount in total_expense_by_month.items()}


def get_incomes_by_month(year):
    """Returns a dictionary where onths as keys and the total income for that month as values."""
    income_by_month_query_set = income_repository.get_incomes_by_month(year)

    income_by_month_dict = format_incomes_by_month_in_dict(
        income_by_month_query_set)

    month_list = expense_repository.get_months_in_list()

    income_by_month_dict_filled = format_empty_incomes_by_month_in_dict(
        income_by_month_dict, month_list)

    return income_by_month_dict_filled


def format_incomes_by_month_in_dict(income_by_month_query_set):

    income_by_month_dict = {item['month'].strftime('%B'): float(
        item['total_amount']) for item in list(income_by_month_query_set)}

    return income_by_month_dict


def format_empty_incomes_by_month_in_dict(income_by_month_dict, month_list):
    income_by_month_dict_filled = {
        label: income_by_month_dict.get(label, 0.0) for label in month_list}
    return income_by_month_dict_filled


def get_expenses_by_selected_month(year, month):
    """Returns total expenses grouped by category for a specific month of a given year."""
    if month:
        return expense_repository.get_expenses_group_by_category_and_month(
            year, month
        )
    return []


def get_selected_year_and_month(request, default_year, default_month):
    """Extracts selected year and month from the request or defaults to the current year and month."""
    selected_year = int(request.GET.get('year', default_year))
    selected_month = int(request.GET.get('month', default_month))
    selected_month_name = calendar.month_name[selected_month]

    return selected_year, selected_month, selected_month_name


def get_distinct_categories():
    """Returns distinct category names."""
    return category_repository.get_categories()


def sort_category_by_month(data):
    # Define the correct order of months
    month_order = expense_repository.get_months_in_list()

    # Function to sort a dictionary based on the month order
    sorted_data = {}
    for category, months in data.items():
        # Sort the months based on the predefined month order
        sorted_months = dict(
            sorted(months.items(), key=lambda x: month_order.index(x[0])))
        sorted_data[category] = sorted_months

    return sorted_data


def sort_by_month(data):
    # Define the correct order of months
    month_order = expense_repository.get_months_in_list()

    sorted_data = dict(
        sorted(data.items(), key=lambda x: month_order.index(x[0])))
    return sorted_data


def get_expenses_by_month(year, month):

    return expense_repository.get_monthly_expenses_by_year(year, month)


def format_brl(value):
    """
    Formats a float value into Brazilian Real currency format (R$ 1.234,90).
    """
    # Ensure value has two decimal places and replace the decimal and thousand separators
    formatted_value = "R$ {:,.2f}".format(value).replace(
        ",", "X").replace(".", ",").replace("X", ".")
    return formatted_value
