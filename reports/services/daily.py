from datetime import timedelta

from django.db.models import Sum
from django.utils.timezone import localdate

from registers.models import Expense

PERIOD_DAYS = (7, 30, 60, 90)
DEFAULT_DAYS = 30
MOVING_AVERAGE_WINDOW = 7


def daily_spending(user, days=DEFAULT_DAYS, category=None):
    """Chart.js data for the last `days` days up to today: daily totals and a 7-day moving average."""
    end = localdate()
    start = end - timedelta(days=days)
    expenses = Expense.objects.filter(user=user, date__gte=start, date__lte=end)
    if category is not None:
        expenses = expenses.filter(category=category)
    totals = {row['date']: float(row['total'])
              for row in expenses.values('date').annotate(total=Sum('amount'))}
    dates = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    daily = [totals.get(day, 0.0) for day in dates]
    moving = []
    for index in range(len(daily)):
        window = daily[max(0, index - MOVING_AVERAGE_WINDOW + 1):index + 1]
        moving.append(sum(window) / len(window))
    return {
        'labels': [day.isoformat() for day in dates],
        'dailyExpenses': daily,
        'movingAverages': moving,
    }
