import csv
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from reports.repository import ExpenseRepository
from utils.dates import get_all_months_tuples

expense_repository = ExpenseRepository()


@login_required
def expense_export(request):
    years = expense_repository.get_distinct_years_in_tuples()
    months = get_all_months_tuples()

    selected_month = request.GET.get('month')
    selected_year = request.GET.get('year')

    expenses = []
    total = Decimal('0.00')

    if selected_month and selected_year:
        expenses = list(
            expense_repository.get_optimized_monthly_expenses_with_relations(
                int(selected_year), int(selected_month)
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
                writer.writerow([
                    e.id,
                    e.date,
                    e.description,
                    e.amount,
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
        'selected_month': int(selected_month) if selected_month else None,
        'selected_year': int(selected_year) if selected_year else None,
    })
