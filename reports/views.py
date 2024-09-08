from django.shortcuts import render
from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import Sum
from registers.models import Expense, Income, Installment
import calendar
from datetime import datetime


def index(request):
    return render(request, 'core/index.html')


def expense_report(request):
    distinct_years = Expense.objects.annotate(year=TruncYear(
        'date')).values('year').distinct().order_by('year')
    distinct_months = Expense.objects.annotate(month=TruncMonth(
        'date')).values('month').distinct().order_by('month')

    months_processed = [(expense['month'].month, calendar.month_name[expense['month'].month])
                        for expense in distinct_months]
    years_processed = [(expense['year'].year, expense['year'].year)
                       for expense in distinct_years]

 # Get current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month

    selected_year = request.GET.get('year', current_year)
    selected_month = request.GET.get('month', current_month)

    if selected_month:
        expenses_by_category = Expense.objects.filter(
            date__year=selected_year, date__month=selected_month).values(
                'category__name').annotate(total_amount=Sum('amount'))
    else:
        expenses_by_category = []

    context = {
        'distinct_years': years_processed,
        'distinct_months': months_processed,
        'selected_month': int(selected_month) if selected_month else None,
        'selected_year': int(selected_year) if selected_year else None,
        'expenses_by_category': expenses_by_category
    }
    return render(request, 'reports/expense_report.html', context)
