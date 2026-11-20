"""Dashboard tabs: resumo (home), gastos, categorias, parcelas, despesas.

Each tab computes only what it shows; the month/year filter comes from `_filters`.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.utils.dates import MONTHS
from django.utils.timezone import localdate

from registers.models import Category, Expense
from reports.services.budget import monthly_budget
from reports.services.categories import category_month_table
from reports.services.daily import DEFAULT_DAYS, PERIOD_DAYS, daily_spending
from reports.services.installments import open_installments
from reports.services.recurring import fixed_expenses_summary
from reports.services.summary import global_balance, spent_on, yearly_charts
from utils.dates import parse_month_year

from utils.http import safe_return_url

# (key, url name, Font Awesome icon, label) in tab-bar order
DASHBOARD_TABS = [
    ('resumo', 'expense_report', 'fa-house', 'Resumo'),
    ('gastos', 'dashboard_spending', 'fa-chart-column', 'Gastos'),
    ('categorias', 'dashboard_categories', 'fa-chart-pie', 'Categorias'),
    ('parcelas', 'dashboard_installments', 'fa-credit-card', 'Parcelas'),
    ('despesas', 'dashboard_expenses', 'fa-list', 'Despesas'),
]


def _filters(request):
    """Month/year filter context shared by every tab; ValueError on a bad month/year."""
    year, month = parse_month_year(request.GET)
    return {
        'selected_year': year,
        'selected_month': month,
        'distinct_years': [d.year for d in Expense.objects.filter(user=request.user).dates('date', 'year')],
        'dashboard_tabs': DASHBOARD_TABS,
    }


def _tab(template, build_context):
    """A dashboard tab view: filter context + the tab's own context, 400 on a bad month/year."""
    @login_required
    def view(request):
        try:
            ctx = _filters(request)
        except ValueError:
            return HttpResponseBadRequest('Mês/ano inválido')
        ctx.update(build_context(request, ctx['selected_year'], ctx['selected_month']))
        return render(request, template, ctx)
    return view


def _resumo(request, year, month):
    today = localdate()
    return {
        'active_tab': 'resumo',
        'fit_screen': True,
        'global_balance': global_balance(request.user),
        'fixed_expenses_summary': fixed_expenses_summary(request.user, year, month),
        'budget_summary': monthly_budget(request.user, year, month),
        'today_total': spent_on(request.user, today),
        'today_date': today,
        'yearly_charts': yearly_charts(request.user, year),
    }


def _gastos(request, year, month):
    return {
        'active_tab': 'gastos',
        'fit_screen': True,
        'budget_summary': monthly_budget(request.user, year, month),
        'daily_spending_data': daily_spending(request.user, DEFAULT_DAYS),
        'daily_spending_days': DEFAULT_DAYS,
        'period_days': PERIOD_DAYS,
        'expense_categories': Category.objects.expense(),
    }


def _categorias(request, year, month):
    return {'active_tab': 'categorias', 'category_table': category_month_table(request.user, year)}


def _parcelas(request, year, month):
    return {'active_tab': 'parcelas', 'installments_progress': open_installments(request.user, year, month)}


def _despesas(request, year, month):
    return {
        'active_tab': 'despesas',
        'monthly_expenses_queryset': (
            Expense.objects.filter(user=request.user).in_month(year, month)
            .select_related('category', 'payment_method', 'reccurring_expense')
            .order_by('date', '-amount')
        ),
    }


expense_report = _tab('reports/tabs/resumo.html', _resumo)
spending = _tab('reports/tabs/gastos.html', _gastos)
categories = _tab('reports/tabs/categorias.html', _categorias)
installments = _tab('reports/tabs/parcelas.html', _parcelas)
expenses = _tab('reports/tabs/despesas.html', _despesas)


@login_required
def budget_breakdown(request):
    """What the Resumo's "expected total" card adds up, for one month."""
    try:
        year, month = parse_month_year(request.GET)
    except ValueError:
        return HttpResponseBadRequest('Mês/ano inválido')
    return render(request, 'reports/budget_breakdown.html', {
        'budget_summary': monthly_budget(request.user, year, month),
        'selected_month': month,
        'selected_year': year,
        'month_label': f"{MONTHS[month]} {year}",
        'back_url': safe_return_url(request, 'back'),
    })
