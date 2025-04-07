from django.db.models import Sum
from registers.models import Income, Expense
from django.utils import timezone


class BalanceService:
    def __init__(self):
        self.balance = 0

    def calculate_global_balance(self):
        today = timezone.now().date()
        total_incomes = Income.objects.filter(date__lte=today).aggregate(
            total_incomes=Sum('amount'))['total_incomes'] or 0
        total_expenses = Expense.objects.filter(date__lte=today).aggregate(
            total_expenses=Sum('amount'))['total_expenses'] or 0
        return total_incomes - total_expenses
