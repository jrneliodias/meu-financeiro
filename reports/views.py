from django.shortcuts import render
from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import Sum
from collections import defaultdict
from registers.models import Expense, Income, Installment
import calendar
from datetime import datetime


def index(request):
    return render(request, 'core/index.html')


def expense_report(request):
    # Get the current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Get distinct years and months
    distinct_years, distinct_months = get_distinct_years_and_months()

    # Get the selected year and month from the request
    selected_year, selected_month, selected_month_name = get_selected_year_and_month(
        request, current_year, current_month)

    # Get expenses grouped by month and category for the current year
    expenses_by_category_by_month, total_expense_by_month = get_expenses_by_month_and_category(
        selected_year)
    print(type(total_expense_by_month))
    # Get expenses for the selected month
    expenses_by_category = get_expenses_by_selected_month(
        selected_year, selected_month)

    # Get distinct category names
    categories = get_distinct_categories()

    # Prepare the context
    context = {
        'expenses_by_category_by_month': expenses_by_category_by_month,
        'total_expense_by_month': total_expense_by_month,
        'categories': categories,
        'current_year': current_year,
        'distinct_years': distinct_years,
        'distinct_months': distinct_months,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_month_name': selected_month_name,
        'expenses_by_category': expenses_by_category
    }

    return render(request, 'reports/expense_report.html', context)


def get_distinct_years_and_months():
    """Returns distinct years and months from the Expense model."""
    distinct_years = Expense.objects.annotate(year=TruncYear(
        'date')).values('year').distinct().order_by('year')
    distinct_months = Expense.objects.annotate(month=TruncMonth(
        'date')).values('month').distinct().order_by('month')

    years_processed = [(expense['year'].year, expense['year'].year)
                       for expense in distinct_years]
    months_processed = [(expense['month'].month, calendar.month_name[expense['month'].month])
                        for expense in distinct_months]

    return years_processed, months_processed


def get_expenses_by_month_and_category(year):
    """
    Returns a dictionary where the key is the category and the value is another dictionary
    with months as keys and the total expenses for that category in that month as values.
    """
    expenses_by_month_category = Expense.objects.filter(date__year=year).annotate(
        month=TruncMonth('date')
    ).values('month', 'category__name').annotate(total_amount=Sum('amount')).order_by('category__name', 'month',)

    _, months_processed = get_distinct_years_and_months()

    months_in_database = list(map(lambda x: x[1], months_processed))

    expenses_by_category = defaultdict(lambda: defaultdict(float))

    total_expense_by_month = defaultdict(float)

    for expense in expenses_by_month_category:
        month = expense['month'].strftime('%B')
        category = expense['category__name']
        total = float(expense['total_amount'])

        expenses_by_category[category][month] = total
        total_expense_by_month[month] += total

    for category, months in expenses_by_category.items():
        for month in months_in_database:
            if month not in months:
                months[month] = 0.00  # Fill with 0.00 if the month is missing
    expenses_by_category_by_month = {category: dict(
        months) for category, months in expenses_by_category.items()}

    expenses_by_category_by_month_sorted = sort_category_by_month(
        expenses_by_category_by_month)

    total_expense_by_month_sorted = sort_by_month(total_expense_by_month)

    return expenses_by_category_by_month_sorted, total_expense_by_month_sorted


def get_expenses_by_selected_month(year, month):
    """Returns total expenses grouped by category for a specific month of a given year."""
    if month:
        return Expense.objects.filter(date__year=year, date__month=month).values(
            'category__name'
        ).annotate(total_amount=Sum('amount')).order_by('category__name')
    return []


def get_selected_year_and_month(request, default_year, default_month):
    """Extracts selected year and month from the request or defaults to the current year and month."""
    selected_year = int(request.GET.get('year', default_year))
    selected_month = int(request.GET.get('month', default_month))
    selected_month_name = calendar.month_name[selected_month]

    return selected_year, selected_month, selected_month_name


def get_distinct_categories():
    """Returns distinct category names."""
    return Expense.objects.values_list('category__name', flat=True).distinct()


def sort_category_by_month(data):
    # Define the correct order of months
    _, month_tuple = get_distinct_years_and_months()
    month_order = list(map(lambda x: x[1], month_tuple))

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
    _, month_tuple = get_distinct_years_and_months()
    month_order = list(map(lambda x: x[1], month_tuple))

    sorted_data = dict(
        sorted(data.items(), key=lambda x: month_order.index(x[0])))
    return sorted_data
