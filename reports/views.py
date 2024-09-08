from django.shortcuts import render
from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import Sum
from registers.models import Expense, Income, Installment
import calendar


def index(request):
    return render(request, 'core/index.html')


def expense_report(request):
    distinct_years = Expense.objects.annotate(year=TruncYear(
        'date')).values('year').distinct().order_by('year')
    distinct_mounths = Expense.objects.annotate(month=TruncMonth(
        'date')).values('month').distinct().order_by('month')

    return render(request, 'reports/expense_report.html', {
        'distinct_years': distinct_years,
        'distinct_mounths': distinct_mounths
    })
