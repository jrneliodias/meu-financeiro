# Design: Exportação de Despesas por Mês/Ano

**Data:** 2026-06-28  
**Status:** Aprovado

## Objetivo

Permitir que o usuário exporte todas as despesas de um mês/ano selecionado em formato CSV, com prévia dos dados antes do download.

## Fluxo do Usuário

1. Usuário acessa `/export/expense`
2. Seleciona mês e ano no formulário e clica "Visualizar"
3. A página recarrega com uma tabela de prévia das despesas do período selecionado, total e botão "Baixar CSV"
4. Clicando "Baixar CSV", o arquivo é baixado automaticamente (`despesas-junho-2026.csv`)
5. Se não há despesas no período, exibe mensagem e desabilita o botão de download

## Arquitetura

### Abordagem escolhida
Opção C — Página dedicada com preview + download. Uma única view lida com os três estados:
- Estado inicial (sem seleção): exibe apenas o formulário
- Estado de prévia (`?month=&year=`): exibe formulário + tabela + botão download
- Estado de download (`?month=&year=&download=1`): retorna `HttpResponse` CSV

### Nova Django app: `export`

Uma app Django independente responsável exclusivamente por exportação de dados.

```
export/
├── __init__.py
├── apps.py
├── urls.py
├── views.py
└── templates/
    └── export/
        └── expense_export.html
```

### Arquivos alterados/criados

| Arquivo | Ação | Descrição |
|---|---|---|
| `export/` | Criar | Nova Django app |
| `export/__init__.py` | Criar | Marcador de pacote Python |
| `export/apps.py` | Criar | Configuração da app (`ExportConfig`) |
| `export/views.py` | Criar | View `expense_export` |
| `export/urls.py` | Criar | Rota `expense` → `expense_export` |
| `export/templates/export/expense_export.html` | Criar | Template com formulário, tabela prévia e botão download |
| `finance/settings.py` | Alterar | Adicionar `'export'` em `INSTALLED_APPS` |
| `finance/urls.py` | Alterar | `path('export/', include('export.urls'))` |

### Sem novas dependências
A geração de CSV usa o módulo `csv` da stdlib Python, já utilizado em `registers/management/commands/export_expenses.py`.

## Detalhes da View (`export/views.py`)

```python
import csv
import calendar
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
            month_name = calendar.month_name[int(selected_month)].lower()
            filename = f"despesas-{month_name}-{selected_year}.csv"
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Data', 'Descrição', 'Valor', 'Categoria',
                             'Método de Pagamento', 'Tipo', 'Criado em'])
            for expense in expenses:
                expense_type = _get_expense_type(expense)
                writer.writerow([
                    expense.id,
                    expense.date,
                    expense.description,
                    expense.amount,
                    expense.category.name if expense.category else 'N/A',
                    expense.payment_method.name if expense.payment_method else 'N/A',
                    expense_type,
                    expense.created_at,
                ])
            return response

    return render(request, 'export/expense_export.html', {
        'expenses': expenses,
        'total': total,
        'years': years,
        'months': months,
        'selected_month': selected_month,
        'selected_year': selected_year,
    })

def _get_expense_type(expense):
    if expense.installment_plan_id:
        return 'Parcela'
    if expense.reccurring_expense_id:
        return 'Recorrente'
    return 'Avulsa'
```

## Colunas do CSV

| Coluna | Fonte |
|---|---|
| ID | `expense.id` |
| Data | `expense.date` |
| Descrição | `expense.description` |
| Valor | `expense.amount` |
| Categoria | `expense.category.name` ou `"N/A"` |
| Método de Pagamento | `expense.payment_method.name` ou `"N/A"` |
| Tipo | `"Parcela"` / `"Recorrente"` / `"Avulsa"` |
| Criado em | `expense.created_at` |

**Nome do arquivo:** `despesas-{mes-nome}-{ano}.csv` (ex: `despesas-junho-2026.csv`)

## Template (`export/templates/export/expense_export.html`)

Estende `core/base.html`. Estrutura:

```
Título: "Exportar Despesas"

[Formulário GET → /export/expense]
  Mês: <select name="month">
  Ano: <select name="year">
  Botão: "Visualizar"

--- Condicional: se mês/ano selecionado ---

  [Se há despesas]
    Subtítulo: "X despesas em {Mês}/{Ano} — Total: R$ X.XXX,XX"
    Botão: "Baixar CSV" → href="?month=X&year=Y&download=1"
    Tabela: ID | Data | Descrição | Valor | Categoria | Pagamento | Tipo | Criado em

  [Se não há despesas]
    Mensagem: "Nenhuma despesa encontrada para {Mês}/{Ano}."
    Botão "Baixar CSV" desabilitado
```

## URL

```
GET /export/expense              → formulário inicial
GET /export/expense?month=6&year=2026            → prévia dos dados
GET /export/expense?month=6&year=2026&download=1 → download do CSV
```

Registrado em `finance/urls.py`:
```python
path('export/', include('export.urls')),
```

Em `export/urls.py`:
```python
urlpatterns = [
    path('expense', views.expense_export, name='expense_export'),
]
```

## Reutilização de código existente

- `ExpenseRepository.get_optimized_monthly_expenses_with_relations(year, month)` — query otimizada com `select_related`
- `expense_repository.get_distinct_years_in_tuples()` — seletor de anos
- `get_all_months_tuples()` — seletor de meses (utils/dates.py)
- Módulo `csv` da stdlib — geração do arquivo (padrão do projeto)

## Segurança

- View protegida por `@login_required`
- Query filtrada por `user=request.user` — usuário vê apenas suas próprias despesas

## Não está no escopo

- Filtros adicionais (categoria, método de pagamento)
- Exportação de múltiplos meses
- Formato Excel ou JSON
- Agendamento automático de exportação
- Models próprios na app `export` (sem necessidade de migrations)
