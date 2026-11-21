"""Generic expense list page.

URL filters: `date=YYYY-MM-DD` | `category_id=[&month=&year=]` | `installments=1&month=&year=`.
"""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils.dates import MONTHS

from registers.models import Category, Expense
from utils.dates import parse_month_year
from utils.http import safe_return_url

RECENT_LIMIT = 50  # a category without a month shows only its latest expenses


def _expenses_and_titles(user, params):
    """(expenses, title, subtitle) for the filters in `params`; None if no filter; ValueError if invalid."""
    mine = Expense.objects.filter(user=user).select_related('category', 'payment_method')
    if params.get('date'):
        day = date.fromisoformat(params['date'])
        return mine.filter(date=day).order_by('date', '-amount'), 'Despesas do dia', day.strftime('%d/%m/%Y')

    has_month = bool(params.get('month') and params.get('year'))
    if has_month:
        year, month = parse_month_year(params)
        in_bill = mine.in_billing_month(year, month).order_by('date', '-amount')
        month_label = f'{str(MONTHS[month]).lower()} de {year}'
    if params.get('category_id'):
        category = Category.objects.filter(pk=int(params['category_id'])).first()
        if category is None:
            raise ValueError('categoria')
        if has_month:
            return in_bill.filter(category=category), category.name, month_label
        latest = mine.filter(category=category).order_by('-date', '-amount')[:RECENT_LIMIT]
        return latest, category.name, f'Últimas {RECENT_LIMIT} despesas'
    if params.get('installments') and has_month:
        return in_bill.filter(installment_plan__isnull=False), 'Parcelas do mês', month_label
    return None


def _by_category(expenses):
    """[(category name, subtotal, expenses)], largest subtotal first; expenses keep their order."""
    groups = {}
    for expense in expenses:
        groups.setdefault(expense.category.name if expense.category else 'Sem categoria', []).append(expense)
    return sorted(((name, sum(e.amount for e in items), items) for name, items in groups.items()),
                  key=lambda group: (-group[1], group[0]))


@login_required
def expense_list_page(request):
    try:
        found = _expenses_and_titles(request.user, request.GET)
    except ValueError:
        return HttpResponseBadRequest('Parâmetros inválidos')
    if found is None:
        return redirect('dashboard_expenses')

    expenses, title, subtitle = found
    expenses = list(expenses)
    groups = _by_category(expenses)
    return render(request, 'reports/expense_list.html', {
        'title': title, 'subtitle': subtitle, 'groups': groups,
        'grouped': len(groups) > 1,  # one category needs no headings (e.g. the category filter)
        'total': sum((e.amount for e in expenses), 0),
        'count': len(expenses),
        'recurring_total': sum((e.amount for e in expenses if e.reccurring_expense_id), 0),
        'installment_total': sum((e.amount for e in expenses if e.installment_plan_id), 0),
        'back_url': safe_return_url(request, 'back'),
    })
