from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.utils.dates import MONTHS
from django.utils.timezone import localdate
from django.utils.translation import gettext as _

from registers.models import Expense, Income
from utils.dates import month_end

# A payment method used to move money into investments, not spending: kept out of the spending charts.
INVESTMENT_PAYMENT_METHOD = 'Investimento'


def _total(queryset):
    return queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0')


def global_balance(user):
    """All income minus all expenses up to the end of the current month."""
    today = localdate()
    end = month_end(today.year, today.month)
    return (_total(Income.objects.filter(user=user, date__lte=end))
            - _total(Expense.objects.filter(user=user, date__lte=end)))


def spent_on(user, day):
    return _total(Expense.objects.filter(user=user, date=day))


def yearly_charts(user, year):
    """Chart.js data per billing month: spending by payment method, and spending vs income."""
    by_method = defaultdict(lambda: [0.0] * 12)
    rows = (Expense.objects.filter(user=user).in_billing_year(year)
            .values('billing_month', 'payment_method__name').annotate(total=Sum('amount'))
            .order_by('billing_month', 'payment_method__name'))
    for row in rows:
        method = row['payment_method__name'] or _('No Payment Method')
        by_method[method][row['billing_month'] - 1] = float(row['total'])
    spending = {method: data for method, data in by_method.items() if method != INVESTMENT_PAYMENT_METHOD}

    income = [0.0] * 12
    rows = (Income.objects.filter(user=user, date__year=year)
            .annotate(month=ExtractMonth('date')).values('month').annotate(total=Sum('amount')))
    for row in rows:
        income[row['month'] - 1] = float(row['total'])

    labels = [str(name) for name in MONTHS.values()]
    return {
        'payment_methods': {
            'labels': labels,
            'datasets': [{'label': method, 'data': data} for method, data in spending.items()],
        },
        'expense_income': {
            'labels': labels,
            'datasets': [
                {'label': _('Total Expenses'), 'data': [sum(month) for month in zip(*spending.values())] or [0.0] * 12},
                {'label': _('Total Income'), 'data': income},
            ],
        },
    }
