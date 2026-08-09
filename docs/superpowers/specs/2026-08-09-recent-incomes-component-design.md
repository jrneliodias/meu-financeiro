# Design: Componente de Entradas Recentes + Fluxo de Sucesso do Income

**Data:** 2026-08-09
**Status:** Aprovado

## Objetivo

1. Adicionar à página de registro de income um componente "Entradas Recentes", equivalente ao "Recent Expenses" já existente na página de expense, com ações **Usar** (autofill) e **Excluir**.
2. Trocar o fluxo de sucesso de `register_income`: hoje redireciona para `expense_success` (outra página); deve, como em expense, mostrar uma mensagem de sucesso na própria página do formulário, sem sair dela.
3. Garantir que todos os textos e labels novos e existentes na página de income tenham internacionalização funcionando (pt_BR e en), sem entradas fuzzy/vazias.

Fora de escopo (decidido no brainstorming): modal de detalhes, link de "editar" (que hoje não existe/funciona nem para expense), mensagens de erro por campo no formulário de income.

## Fluxo do Usuário

1. Usuário acessa `/register/income`.
2. Abaixo do formulário, vê a seção "Entradas Recentes" carregada via AJAX (até 10 últimas, mais recentes primeiro).
3. Cada card mostra descrição, valor formatado, data e categoria, com botões **Usar** e **Excluir**.
4. **Usar** busca os dados via AJAX e preenche o formulário (description, amount, date, category) — sem scroll extra necessário, já que o form fica acima da lista.
5. **Excluir** pede confirmação (`confirm()`), remove via AJAX e recarrega a lista.
6. Ao submeter o formulário com sucesso, a página recarrega (`redirect('register_income')`) mostrando uma mensagem de sucesso (`messages.success`) e a lista de entradas recentes atualizada — sem navegar para outra página.

## Arquitetura

Replica o padrão já usado por expense (`RecentExpenseRepository` → `RecentExpenseService` → view AJAX → JS module), com uma versão mais enxuta porque `Income` não tem `payment_method`, `installment_plan` nem `reccurring_expense`.

### Arquivos criados

| Arquivo | Descrição |
|---|---|
| `registers/repository/recent_income_repository.py` | `RecentIncomeRepository`: `get_recent_incomes_for_user(user, limit=ExpenseConstants.RECENT_EXPENSES_LIMIT)` e `get_income_by_id_for_user(income_id, user)`, com `select_related('category')`. |
| `registers/services/recent_income_service.py` | `RecentIncomeService`: `get_recent_incomes(user)`, `get_income_for_autofill(income_id, user)`, formatação de moeda (mesma lógica de `_format_currency` do expense). |
| `registers/templates/register/components/recent_incomes_table.html` | Mirror de `recent_expenses_table.html`, IDs prefixados com `recentIncomes*`, título `{% trans "Recent Incomes" %}`. |
| `registers/static/js/recent_incomes.js` | Mirror enxuto de `recent_expenses.js`: sem modal/details — só load, render card (Usar/Excluir), autofill, delete. Usa `window.RecentIncomesI18n`. |

### Arquivos alterados

| Arquivo | Alteração |
|---|---|
| `registers/urls.py` | + `income/recent/`, `income/<int:pk>/autofill/`, `income/<int:pk>/delete/`. |
| `registers/views.py` | + `recent_income_service = RecentIncomeService()`; + views `recent_incomes_ajax`, `income_autofill_ajax`, `delete_income` (cópias enxutas das equivalentes de expense); `register_income` passa a fazer `messages.success(...)` + `redirect('register_income')` em vez de `redirect('expense_success')`, e passa `quick_fill_options`-like nada (income não tem quick fill) — só precisa renderizar `form` como já faz. |
| `registers/templates/register/income_form.html` | + bloco `{% if messages %}` (igual ao de expense_form.html); + `{% include "register/components/recent_incomes_table.html" %}`; + `<script>` com `window.RecentIncomesI18n` e `<script src="{% static 'js/recent_incomes.js' %}">`; template passa a `{% load ... static %}`. |
| `locale/pt_BR/LC_MESSAGES/django.po` e `locale/en/LC_MESSAGES/django.po` | Novas entradas para todas as strings novas (título da seção, botões, estados vazio/erro/loading, mensagem de sucesso do income, textos do JS). Compilar com `compilemessages` depois. |

### Sem novas dependências
Reusa fetch/vanilla JS já usado em `recent_expenses.js`, e o padrão Django de `messages` já usado em `register_expense`.

## Detalhes de Backend

### `recent_income_repository.py`
```python
class RecentIncomeRepository:
    def get_recent_incomes_for_user(self, user, limit=ExpenseConstants.RECENT_EXPENSES_LIMIT):
        return (
            Income.objects
            .filter(user=user)
            .select_related('category')
            .order_by('-updated_at')[:limit]
        )

    def get_income_by_id_for_user(self, income_id, user):
        try:
            return Income.objects.select_related('category').get(id=income_id, user=user)
        except Income.DoesNotExist:
            return None
```
(Confirmado: `Income` tem `updated_at` via `auto_now=True`, igual a `Expense`.)

### `recent_income_service.py`
Mesma forma de `RecentExpenseService`, mas só com `_format_income_for_list` e `_format_income_for_autofill` (sem installment/recurring/payment_method).

### Views novas em `views.py` (padrão idêntico às de expense, trocando `Expense`→`Income` e serviço)
- `recent_incomes_ajax(request)` — GET, retorna JSON `{success, incomes, count}`.
- `income_autofill_ajax(request, pk)` — GET, retorna JSON `{success, form_data}`.
- `delete_income(request, pk)` — POST, verifica ownership, deleta, retorna JSON `{success}`.

### `register_income` (alteração)
```python
messages.success(
    request,
    _("Income %(income)s has been registered.") % {'income': str(income)}
)
return redirect('register_income')
```

## Frontend

`recent_incomes.js` segue a mesma estrutura de `recent_expenses.js`, removendo tudo relacionado a modal/detalhes/edit:
- `ENDPOINTS`: `RECENT: '/register/income/recent/'`, `AUTOFILL: '/register/income/{id}/autofill/'`, `DELETE: '/register/income/{id}/delete/'`.
- Card renderiza: descrição, valor, data, categoria, botões Usar/Excluir.
- `autofillForm` popula `id_description`, `id_amount`, `id_date`, `id_category` (select simples, sem autocomplete).
- `deleteIncome` com `confirm()` + refresh da lista.

`income_form.html` ganha os mesmos three blocos que expense_form.html tem: mensagens, include do componente, scripts com objeto de i18n.

## i18n

Novas `msgid`s necessárias (a confirmar contra os textos finais do template/JS):
- "Recent Incomes", "No recent incomes found", "Loading incomes...", "Refresh list" (já existe, reusar)
- "Use", "Delete" (já existem, reusar de expense)
- "Do you really want to delete the income" (novo, singular de expense)
- "Error loading incomes", "Error deleting income", "Error loading data" (checar reuso das genéricas já existentes)
- "Income %(income)s has been registered." (nova, mensagem de sucesso)

Processo: `python manage.py makemessages -l pt_BR -l en` → preencher manualmente as novas entradas em ambos `.po` (sem deixar `fuzzy` ou vazio, seguindo o padrão já usado no repo) → `python manage.py compilemessages`.

## Testes

Segue a convenção do repo (`registers/tests/`). Não framework novo, um teste simples por peça de lógica não trivial:
- `RecentIncomeService`: teste de formatação de moeda e de que `get_recent_incomes` retorna lista formatada respeitando o filtro por usuário.
- `register_income` view: teste de que POST válido cria o Income, adiciona mensagem de sucesso e redireciona para `register_income` (não mais para `expense_success`).
- `delete_income` view: teste de que só o dono pode excluir.
