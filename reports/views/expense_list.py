"""Página genérica de lista de despesas (substitui os modais de lista).

Filtros na URL: `date=YYYY-MM-DD` | `category_id=[&month=&year=]` | `installments=1&month=&year=`.
"""
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from registers.models import Category

from ._common import expense_repository

RECENT_LIMIT = 50  # categoria sem mês: só as mais recentes
MONTHS_PT = ['', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
             'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']


def _parse(request):
    """Lê os filtros; devolve (kwargs do repositório, título, subtítulo) ou levanta ValueError."""
    q = request.GET
    month_year = None
    if q.get('month') and q.get('year'):
        month, year = int(q['month']), int(q['year'])
        if not (1 <= month <= 12 and 2000 <= year <= 2100):
            raise ValueError('mês/ano')
        month_year = (month, year, f'{MONTHS_PT[month]} de {year}')

    if q.get('date'):
        day = datetime.strptime(q['date'], '%Y-%m-%d').date()
        return {'on_date': day}, 'Despesas do dia', day.strftime('%d/%m/%Y')
    if q.get('category_id'):
        category = Category.objects.filter(pk=int(q['category_id'])).first()
        if category is None:
            raise ValueError('categoria')
        if month_year:
            return ({'category_id': category.pk, 'month': month_year[0], 'year': month_year[1]},
                    category.name, month_year[2])
        return ({'category_id': category.pk, 'limit': RECENT_LIMIT},
                category.name, f'Últimas {RECENT_LIMIT} despesas')
    if q.get('installments') and month_year:
        return ({'installments': True, 'month': month_year[0], 'year': month_year[1]},
                'Parcelas do mês', month_year[2])
    return None, '', ''


@login_required
def expense_list_page(request):
    try:
        filters, title, subtitle = _parse(request)
    except ValueError:
        return HttpResponseBadRequest('Parâmetros inválidos')
    if filters is None:
        return redirect('dashboard_expenses')

    expenses = list(expense_repository.get_expense_list(request.user, **filters))
    total = sum((e.amount for e in expenses), 0)
    back = request.GET.get('back', '')
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = ''
    return render(request, 'reports/expense_list.html', {
        'title': title, 'subtitle': subtitle, 'expenses': expenses,
        'total': total, 'count': len(expenses),
        'recurring_total': sum((e.amount for e in expenses if e.reccurring_expense_id), 0),
        'installment_total': sum((e.amount for e in expenses if e.installment_plan_id), 0),
        'back_url': back,
    })
