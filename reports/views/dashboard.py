"""Dashboard dividido em abas: resumo (home), gastos, categorias, parcelas, despesas.

Cada aba calcula só o que mostra. O filtro de mês/ano vem de `_filters`.
"""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from registers.models import Category
from reports.services import ExpenseService
from reports.services.daily_expense_calculator import DailyExpenseCalculator
from utils.dates import get_all_months, get_all_months_tuples, get_current_date

from ._common import (
    balance_service, budget_estimate_service, expense_repository, format_brl,
    get_selected_year_and_month, income_repository, installment_calculator,
    recurring_expense_service,
)

TEMPLATE_DIR = 'reports/'

# (chave, nome da url, ícone Font Awesome, rótulo) na ordem da barra de abas
DASHBOARD_TABS = [
    ('resumo', 'expense_report', 'fa-house', 'Resumo'),
    ('gastos', 'dashboard_spending', 'fa-chart-column', 'Gastos'),
    ('categorias', 'dashboard_categories', 'fa-chart-pie', 'Categorias'),
    ('parcelas', 'dashboard_installments', 'fa-credit-card', 'Parcelas'),
    ('despesas', 'dashboard_expenses', 'fa-list', 'Despesas'),
]


def _filters(request):
    """Contexto do filtro de mês/ano, comum a todas as abas."""
    current_year, current_month = get_current_date()
    year, month, _name = get_selected_year_and_month(request, current_year, current_month)
    return {
        'selected_year': year,
        'selected_month': month,
        'distinct_years': expense_repository.get_distinct_years_in_tuples(),
        'distinct_months': get_all_months_tuples(),
        'dashboard_tabs': DASHBOARD_TABS,
    }


def _expense_service(year):
    return ExpenseService(expense_repository, income_repository, year=year)


@login_required
def expense_report(request):
    """Aba Resumo (home): saldo, cards, orçamento e gráfico receita x despesa."""
    ctx = _filters(request)
    month, year = ctx['selected_month'], ctx['selected_year']

    installment_summary = installment_calculator.get_monthly_installment_summary(
        month=month, year=year, user=request.user)
    regular_total = expense_repository.get_monthly_regular_expenses_total(
        month=month, year=year, user=request.user)
    budget = budget_estimate_service.get_monthly_budget_summary(
        request.user, month, year,
        monthly_installment_total=installment_summary['total_amount'])
    budget.total_regular = regular_total
    budget.adjusted_expected = budget.total_expected + regular_total

    today = date.today()
    ctx.update({
        'active_tab': 'resumo',
        'global_balance': balance_service.calculate_global_balance(),
        'fixed_expenses_summary': recurring_expense_service.get_fixed_expenses_summary(
            request.user, month, year),
        'installment_monthly_summary': installment_summary,
        'regular_expenses_summary': {
            'total_amount': regular_total,
            'formatted_total': format_brl(float(regular_total)),
        },
        'today_total': float(expense_repository.get_total_by_date(today)),
        'today_date': today.strftime('%Y-%m-%d'),
        'budget_summary': budget,
        'monthly_expense_income_datasets':
            _expense_service(year).get_optimized_payment_method_data()['combined_datasets'],
    })
    return render(request, TEMPLATE_DIR + 'tabs/resumo.html', ctx)


@login_required
def spending(request):
    """Aba Gastos: gráfico de gasto diário."""
    ctx = _filters(request)
    ctx.update({
        'active_tab': 'gastos',
        'daily_spending_data': get_daily_spending_data(
            expense_repository, ctx['selected_year'], ctx['selected_month']),
        'expense_categories': Category.objects.filter(type='expense').order_by('name'),
    })
    return render(request, TEMPLATE_DIR + 'tabs/gastos.html', ctx)


@login_required
def categories(request):
    """Aba Categorias: tabela por categoria/mês e gráfico por forma de pagamento."""
    ctx = _filters(request)
    all_months = get_all_months()
    service = _expense_service(ctx['selected_year'])
    data = service.get_optimized_expenses_data(all_months)
    ctx.update({
        'active_tab': 'categorias',
        'all_months': all_months,
        'formatted_expenses_by_category': {
            category: [format_brl(totals.get(m, 0.0)) for m in all_months]
            for category, totals in data['expenses_by_category_by_month'].items()
        },
        'formatted_totals': [
            format_brl(data['total_expense_by_month'].get(m, 0.0)) for m in all_months],
        'calculated_monthy_payment_method_expense_totals':
            service.get_optimized_payment_method_data()['datasets'],
    })
    return render(request, TEMPLATE_DIR + 'tabs/categorias.html', ctx)


@login_required
def installments(request):
    """Aba Parcelas: progresso das compras parceladas."""
    ctx = _filters(request)
    ctx.update({
        'active_tab': 'parcelas',
        'installments_progress': installment_calculator.get_installments_summary(
            reference_month=ctx['selected_month'], reference_year=ctx['selected_year']),
    })
    return render(request, TEMPLATE_DIR + 'tabs/parcelas.html', ctx)


@login_required
def expenses(request):
    """Aba Despesas: lista completa do mês."""
    ctx = _filters(request)
    ctx.update({
        'active_tab': 'despesas',
        'monthly_expenses_queryset': _expense_service(ctx['selected_year'])
            .get_optimized_monthly_expenses(ctx['selected_month']),
    })
    return render(request, TEMPLATE_DIR + 'tabs/despesas.html', ctx)


def get_daily_spending_data(expense_repository, year, month):
    """
    Get daily spending data for the chart.

    Why separate function? Maintains the modular approach of your existing code
    and makes testing easier.
    """
    try:
        daily_calculator = DailyExpenseCalculator(expense_repository, year, month)

        # Get trend data for the last 30 days
        trend_data = daily_calculator.get_daily_spending_trends(days=30)

        # Format data for Chart.js - ensure all values are JSON-serializable
        sorted_dates = sorted(trend_data['daily_expenses'].keys())

        result = {
            'labels': [str(date) for date in sorted_dates],  # Ensure strings
            'dailyExpenses': [float(trend_data['daily_expenses'][date]) for date in sorted_dates],  # Ensure floats
            'movingAverages': [float(trend_data['moving_averages'].get(date, 0)) for date in sorted_dates],  # Ensure floats
            'totalSpending': float(trend_data['total_spending']),  # Ensure float
            'averageDaily': float(trend_data['average_daily'])  # Ensure float
        }

        return result

    except Exception as e:
        print(f"ERROR in get_daily_spending_data: {e}")
        import traceback
        print(f"ERROR traceback: {traceback.format_exc()}")

        # Return empty but valid data structure to prevent template errors
        return {
            'labels': [],
            'dailyExpenses': [],
            'movingAverages': [],
            'totalSpending': 0.0,
            'averageDaily': 0.0
        }

