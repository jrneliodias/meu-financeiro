import csv
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

from registers.models import Expense
from utils.dates import parse_month_year


def _csv_response(expenses, year, month, decimal_sep):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="despesas-{year}-{month:02d}.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Data', 'Descrição', 'Valor', 'Categoria', 'Método de Pagamento', 'Tipo', 'Criado em'])
    for e in expenses:
        writer.writerow([
            e.id, e.date, e.description, f"{e.amount:.2f}".replace('.', decimal_sep),
            e.category.name if e.category else 'N/A',
            e.payment_method.name if e.payment_method else 'N/A',
            e.kind_label, e.created_at,
        ])
    return response


@login_required
def expense_export(request):
    try:
        year, month = parse_month_year(request.GET)
    except ValueError:
        return HttpResponseBadRequest('Mês/ano inválido')
    decimal_sep = request.GET.get('decimal_sep') if request.GET.get('decimal_sep') in ('.', ',') else '.'
    form_submitted = 'month' in request.GET
    mine = Expense.objects.filter(user=request.user)
    expenses = []
    if form_submitted:
        expenses = list(mine.in_month(year, month)
                        .select_related('category', 'payment_method').order_by('date', '-amount'))
        if 'download' in request.GET:
            return _csv_response(expenses, year, month, decimal_sep)

    return render(request, 'export/expense_export.html', {
        'expenses': expenses,
        'total': sum((e.amount for e in expenses), Decimal('0.00')),
        'years': [d.year for d in mine.dates('date', 'year')],
        'selected_month': month,
        'selected_year': year,
        'form_submitted': form_submitted,
        'decimal_sep': decimal_sep,
    })
