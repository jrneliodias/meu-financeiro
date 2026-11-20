from collections import defaultdict

from django.db.models import Sum
from django.utils.translation import gettext as _

from registers.models import Expense


def category_month_table(user, year):
    """Spending per category and billing month of `year`, categories sorted by name."""
    months_by_category = defaultdict(lambda: [0.0] * 12)
    category_ids = {}
    rows = (Expense.objects.filter(user=user).in_billing_year(year)
            .values('billing_month', 'category_id', 'category__name').annotate(total=Sum('amount')))
    for row in rows:
        name = row['category__name'] or _('No Category')
        months_by_category[name][row['billing_month'] - 1] += float(row['total'])
        category_ids[name] = row['category_id']
    categories = [
        {'name': name, 'id': category_ids[name], 'months': months}
        for name, months in sorted(months_by_category.items(), key=lambda item: item[0].lower())
    ]
    return {
        'categories': categories,
        'totals': [sum(month) for month in zip(*(c['months'] for c in categories))] or [0.0] * 12,
    }
