from django.db.models import Sum
from registers.models import Income, Expense
from utils.dates import get_last_day_of_current_month


class BalanceService:
    def __init__(self):
        self.balance = 0

    def calculate_global_balance(self):
        end_date = get_last_day_of_current_month()
        total_incomes = Income.objects.filter(date__lte=end_date).aggregate(
            total_incomes=Sum('amount'))['total_incomes'] or 0
        total_expenses = Expense.objects.filter(date__lte=end_date).aggregate(
            total_expenses=Sum('amount'))['total_expenses'] or 0
        return total_incomes - total_expenses
