from django.shortcuts import render
from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import Sum
from registers.models import Expense, Income, Installment


def index(request):
    return render(request, 'core/index.html')


def expense_report(request):
    pass
