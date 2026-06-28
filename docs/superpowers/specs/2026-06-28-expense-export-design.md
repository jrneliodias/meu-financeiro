# Design: Exportação de Despesas por Mês/Ano

**Data:** 2026-06-28  
**Status:** Aprovado

## Objetivo

Permitir que o usuário exporte todas as despesas de um mês/ano selecionado em formato CSV, com prévia dos dados antes do download.

## Fluxo do Usuário

1. Usuário acessa `/register/export-expenses/`
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

### Arquivos alterados/criados

| Arquivo | Ação | Descrição |
|---|---|---|
| `registers/urls.py` | Alterar | Adicionar rota `export-expenses/` |
| `registers/views.py` | Alterar | Adicionar view `export_expenses` |
| `registers/templates/register/expense_export.html` | Criar | Template com formulário, tabela prévia e botão download |

### Sem novas dependências
A geração de CSV usa o módulo `csv` da stdlib Python, já utilizado em `export_expenses.py`.

## Detalhes da View (`export_expenses`)

```python
@login_required
def export_expenses(request):
    # Popula seletores
    years = expense_repository.get_distinct_years_in_tuples()
    months = get_all_months_tuples()

    selected_month = request.GET.get('month')
    selected_year = request.GET.get('year')

    expenses = []
    total = Decimal('0.00')

    if selected_month and selected_year:
        expenses = expense_repository.get_optimized_monthly_expenses_with_relations(
            int(selected_year), int(selected_month)
        ).filter(user=request.user)
        total = sum(e.amount for e in expenses)

        if 'download' in request.GET:
            # Retorna HttpResponse com CSV
            ...

    return render(request, 'register/expense_export.html', {
        'expenses': expenses,
        'total': total,
        'years': years,
        'months': months,
        'selected_month': selected_month,
        'selected_year': selected_year,
    })
```

**Determinação do tipo de despesa:**
- `expense.installment_plan_id` não nulo → `"Parcela"`
- `expense.reccurring_expense_id` não nulo → `"Recorrente"`
- Ambos nulos → `"Avulsa"`

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

## Template (`expense_export.html`)

Estende `core/base.html`. Estrutura:

```
Título: "Exportar Despesas"

[Formulário GET]
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
