import csv
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from reports.repository import ExpenseRepository
from utils.dates import get_all_months_tuples, get_current_date

expense_repository = ExpenseRepository()


@login_required
def expense_export(request):
    years = expense_repository.get_distinct_years_in_tuples()
    months = get_all_months_tuples()

    current_year, current_month = get_current_date()
    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))
    form_submitted = 'month' in request.GET

    expenses = []
    total = Decimal('0.00')

    decimal_sep = request.GET.get('decimal_sep', '.')
    if decimal_sep not in ('.', ','):
        decimal_sep = '.'

    if form_submitted:
        expenses = list(
            expense_repository.get_optimized_monthly_expenses_with_relations(
                selected_year, selected_month
            ).filter(user=request.user)
        )
        total = sum(e.amount for e in expenses)

        if 'download' in request.GET:
            filename = f"despesas-{selected_year}-{int(selected_month):02d}.csv"
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Data', 'Descrição', 'Valor', 'Categoria',
                             'Método de Pagamento', 'Tipo', 'Criado em'])
            for e in expenses:
                if e.installment_plan_id:
                    kind = 'Parcela'
                elif e.reccurring_expense_id:
                    kind = 'Recorrente'
                else:
                    kind = 'Avulsa'
                amount = f"{e.amount:.2f}".replace('.', decimal_sep)
                writer.writerow([
                    e.id,
                    e.date,
                    e.description,
                    amount,
                    e.category.name if e.category else 'N/A',
                    e.payment_method.name if e.payment_method else 'N/A',
                    kind,
                    e.created_at,
                ])
            return response

    return render(request, 'export/expense_export.html', {
        'expenses': expenses,
        'total': total,
        'years': years,
        'months': months,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'form_submitted': form_submitted,
        'decimal_sep': decimal_sep,
    })
