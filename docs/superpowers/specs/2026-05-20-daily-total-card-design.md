# Design: Card "Total do Dia" no Dashboard

**Data:** 2026-05-20  
**Status:** Aprovado

## Objetivo

Adicionar um terceiro card no header do dashboard (ao lado de "Saldo" e "Despesas Fixas") que exibe o total de gastos do dia atual. Ao clicar no card, abre o modal de detalhes de despesas do dia — o mesmo modal já utilizado no gráfico de gastos diários.

## Abordagem Escolhida

**Opção C — Server-side com data-attribute.**  
O total do dia é calculado no view Django e injetado no template. O card carrega com o valor já renderizado no HTML. Um `data-date` attribute no card contém a data de hoje. O clique dispara a função JS existente de detalhes do modal, passando essa data.

## Arquitetura

### 1. View — `reports/views.py`

- No `expense_report` view, calcular o total de despesas de hoje usando `ExpenseRepository.get_expenses_by_date(date.today())` já existente.
- Agregar o total somando o campo `amount` dos resultados.
- Adicionar ao contexto:
  - `today_total`: `float` — soma de todas as despesas de hoje
  - `today_date`: `str` — data de hoje em formato `YYYY-MM-DD`

### 2. Repositório — `reports/repository/expense_repository.py`

- Verificar se já existe método que retorna o total agregado para uma data (não apenas a lista).
- Se não existir, adicionar `get_total_by_date(target_date: date) -> Decimal` que faz `aggregate(Sum('amount'))` filtrado por `date=target_date`.
- O método `get_expenses_by_date` já existe; se retornar os valores com `amount`, a view pode somar sem novo método no repositório.

### 3. Novo template — `reports/templates/reports/components/daily_total_card.html`

- Estrutura visual idêntica ao `fixed_expenses_card.html` (`bg-zinc-800/40 p-3 md:p-4 py-2 rounded-lg`).
- Adicionar `cursor-pointer` e efeito `hover:bg-zinc-700/40` para indicar clicabilidade.
- Elementos:
  - `<p>`: label "Gasto Hoje:"
  - `<span id="dailyTotalDisplay">`: valor formatado em BRL (cor branca)
  - `data-date="{{ today_date }}"` no elemento raiz (div clicável)
- Script inline formata o valor via `Intl.NumberFormat` (padrão do projeto).

### 4. JS — Expor função de modal globalmente

Atualmente `showExpenseDetails(date)` é um método da classe `DailySpendingChart` definida dentro do `daily_spending_chart.html`. O card não tem acesso a essa instância.

**Solução:** após a instanciação de `dailyChart` no script existente, expor no `window`:

```js
window.showExpenseDetailsForDate = (date) => dailyChart.showExpenseDetails(date);
```

O card então chama `onclick="window.showExpenseDetailsForDate(this.dataset.date)"`.

### 5. `filter_form.html` — Incluir o novo card

Na `div` que já contém os cards "Saldo" e "Despesas Fixas":

```html
{% include "reports/components/daily_total_card.html" with today_total=today_total today_date=today_date %}
```

## Fluxo de Dados

```
expense_report view
  └─ get_expenses_by_date(today) → soma amount → today_total, today_date
        └─ context → daily_total_card.html
              └─ data-date="{{ today_date }}"
              └─ onclick → window.showExpenseDetailsForDate(date)
                    └─ DailySpendingChart.showExpenseDetails(date)
                          └─ AJAX /expense-details/?date=YYYY-MM-DD
                                └─ modal existente renderiza resultado
```

## Arquivos Modificados

| Arquivo | Mudança |
|---|---|
| `reports/views.py` | Adicionar `today_total` e `today_date` ao contexto do `expense_report` |
| `reports/repository/expense_repository.py` | Adicionar `get_total_by_date` se necessário |
| `reports/templates/reports/components/daily_total_card.html` | Criar novo componente |
| `reports/templates/reports/components/daily_spending_chart.html` | Expor `window.showExpenseDetailsForDate` |
| `reports/templates/reports/components/filter_form.html` | Incluir o novo card |

## O que NÃO muda

- Modal de detalhes de despesas: nenhuma alteração
- Endpoint `/expense-details/`: nenhuma alteração
- Lógica do gráfico diário: nenhuma alteração (apenas expõe função no `window`)

## Critérios de Aceitação

1. O card "Gasto Hoje" aparece ao lado de "Saldo" e "Despesas Fixas" no header
2. O valor exibido é o total de todas as despesas do dia atual formatado em BRL
3. O card tem visual de clicável (cursor pointer + hover)
4. Clicar no card abre o modal de detalhes com as despesas de hoje
5. O modal exibe: total, nº de despesas, recorrentes, parcelas, por categoria e lista completa
6. Se não houver despesas hoje, o card exibe R$ 0,00 e o modal mostra estado vazio
