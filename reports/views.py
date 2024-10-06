from django.shortcuts import render
from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import Sum
from collections import defaultdict
from registers.models import Expense, Income, PaymentMethod
import calendar
from datetime import datetime
from pprint import pprint
from django.forms.models import model_to_dict
from calendar import monthrange


def index(request):
    return render(request, 'core/index.html')


def expense_report(request):
    # Get the current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Get distinct years and months
    distinct_years, distinct_months = get_distinct_years_and_months()
    month_by_year = get_months_by_year(current_year)

    # Get the selected year and month from the request
    selected_year, selected_month, selected_month_name = get_selected_year_and_month(
        request, current_year, current_month)

    # Get expenses grouped by month and category for the current year
    expenses_by_category_by_month, total_expense_by_month, total_expense_by_month_list = get_expenses_by_month_and_category(
        selected_year)
    print(type(total_expense_by_month))
    # Get expenses for the selected month
    expenses_by_category = get_expenses_by_selected_month(
        selected_year, selected_month)

    # Get distinct category names
    categories = get_distinct_categories()
    print(get_payment_methods_and_start_billing_days())
    print(get_total_expenses_amount_by_payment_method_and_month(
        month_by_year, selected_year))

    # Get incomes by month
    incomes_by_month = get_incomes_by_month(selected_year)

    formatted_expenses = [
        total_expense_by_month_list.get(month_name, 'R$ 0,00') for _, month_name in distinct_months
    ]

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
        'expenses_by_category': expenses_by_category
    }

    return render(request, 'reports/expense_report.html', context)


def get_payment_methods_and_start_billing_days():
    payment_methods_db = PaymentMethod.objects.all()
    data = []

    if payment_methods_db:
        for payment_method in payment_methods_db:
            method_dict = model_to_dict(payment_method)
            data.append(method_dict)
    return data


def get_total_expenses_amount_by_payment_method_and_month(month_list: list[tuple[str, str]], year: int):

    interval_filter = calculate_time_interval_for_custom_start_billing_day(
        month_list, year)

    for interval in interval_filter:
        previous_month_24th = interval[1]
        current_month_24th = interval[2]
        credit_expenses = Expense.objects.filter(
            payment_method__start_billing_day=24,  # Credit card payments start on 24th
            date__gte=previous_month_24th,
            date__lte=current_month_24th
        ).values('category__name').annotate(total_amount=Sum('amount'))
        expense_by_category = {}
        for credit_expense in credit_expenses:
            category = credit_expense['category__name']
            total_amount = credit_expense['total_amount']
            if category in expense_by_category:
                expense_by_category[category] += total_amount
            else:
                expense_by_category[category] = total_amount

        pprint(expense_by_category)


def calculate_time_interval_for_custom_start_billing_day(month_list: list[tuple[str, str]], year: int):
    payment_methods = get_payment_methods_and_start_billing_days()
    interval_filter = []
    for payment_method in payment_methods:
        if (payment_method['start_billing_day'] == 1):
            continue
        print(payment_method['name'])
        for month_num, month_name in month_list:
            previous_month = int(month_num) - 1 if int(month_num) > 1 else 12
            current_month_start = datetime(
                year, previous_month, payment_method['start_billing_day'])
            current_month_end = datetime(
                year, month_num, payment_method['start_billing_day'])
            interval_filter.append(
                (month_name, current_month_start, current_month_end))
    return interval_filter


def calculate_total_expenses_amount_by_payment_method_and_month(month: int, year: int, payment_method: dict):

    expenses_by_payment = Expense.objects.filter(date__year=year
                                                 ).values('payment_method__name'
                                                          ).annotate(month=TruncMonth('date')
                                                                     ).annotate(total_amount=Sum('amount')
                                                                                )

    return expenses_by_payment


def get_months_by_year(year):
    months_set = Expense.objects.filter(date__year=year).annotate(month=TruncMonth(
        'date')).values('month').distinct().order_by('month')
    return [(expense['month'].month, calendar.month_name[expense['month'].month])
            for expense in months_set]


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

        expenses_by_category[category][month] = format_brl(total)
        total_expense_by_month[month] += total

    for category, months in expenses_by_category.items():
        for month in months_in_database:
            if month not in months:
                months[month] = 0.00  # Fill with 0.00 if the month is missing
    expenses_by_category_by_month = {category: dict(
        months) for category, months in expenses_by_category.items()}

    expenses_by_category_by_month_sorted = sort_category_by_month(
        expenses_by_category_by_month)

    total_expense_by_month_list = {month: format_brl(
        amount) for month, amount in total_expense_by_month.items()}
    pprint(total_expense_by_month_list)

    total_expense_by_month_sorted = sort_by_month(total_expense_by_month)

    return expenses_by_category_by_month_sorted, total_expense_by_month_sorted, total_expense_by_month_list


def get_incomes_by_month(year):
    """Returns a dictionary where onths as keys and the total income for that month as values."""
    income_by_month_query_set = Income.objects.filter(date__year=year).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(total_amount=Sum('amount')).order_by('month',)

    income_by_month_dict = {item['month'].strftime('%B'): float(
        item['total_amount']) for item in list(income_by_month_query_set)}

    _, month_tuple = get_distinct_years_and_months()

    income_by_month_dict_filled = {
        label: income_by_month_dict.get(label, 0.0) for _, label in month_tuple}

    return income_by_month_dict_filled


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


def format_brl(value):
    """
    Formats a float value into Brazilian Real currency format (R$ 1.234,90).
    """
    # Ensure value has two decimal places and replace the decimal and thousand separators
    formatted_value = "R$ {:,.2f}".format(value).replace(
        ",", "X").replace(".", ",").replace("X", ".")
    return formatted_value
