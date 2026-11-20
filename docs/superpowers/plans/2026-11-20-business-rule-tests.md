# Testes das Regras de Negócio — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** cobrir com testes de comportamento cada regra de negócio que hoje não tem teste, sem mudar código de produção.

**Architecture:** as regras vivem nos modelos (`registers/models.py`), nas funções de `reports/services/*`, nos formulários (`registers/forms.py`), no CSV (`registers/csv/`), na exportação (`export/views.py`) e em `utils/`. Cada tarefa cria ou estende um módulo de teste por área e testa pela interface pública (função de serviço, método do modelo ou página/endpoint), nunca por detalhes internos.

**Tech Stack:** Django 5.1 `TestCase`, SQLite em memória, `unittest.mock.patch` só para o relógio.

**Spec:** as regras estão descritas em `CLAUDE.md` (seção "Models own the domain rules", `reports`, `registers`) e em `docs/refactor/2026-11-20-decision-log.md` (comportamentos e decisões). Os valores esperados abaixo foram conferidos rodando o código atual num banco de rascunho.

## Global Constraints

- Rodar testes sempre com `DATABASE_URL=` (o `.env` aponta para o banco de produção): `DATABASE_URL= venv/bin/python manage.py test <módulo>`.
- Nenhuma alteração em código de produção. Se um teste falhar contra o código atual, **não** ajuste o teste ao código: pare e reporte (é um bug ou uma decisão de produto).
- Testar comportamento: retorno de função pública, estado do banco, status/HTML/JSON de página. Nada de `context[...]` de template, nomes de template, contagem de queries ou chamadas internas.
- Relógio: use `today_is(date)` (Tarefa 0), que faz `patch('django.utils.timezone.now')`; não faça patch de `localdate` no módulo que o importa.
- Datas e meses na ordem `(year, month)` em todas as chamadas de serviço e modelo.
- Mensagens traduzidas: use `translation.override('en')` quando a asserção depender do texto.
- Nomes de teste em inglês, no padrão `test_<comportamento>` dos módulos existentes.

## Review Focus

1. **Despesa sem forma de pagamento**: cai na fatura do mês do calendário (não há dia de início de cobrança). Teste na Tarefa 1.
2. **Virada de dia em São Paulo vs UTC**: às 23h de 10/03 em São Paulo (02h UTC de 11/03), "hoje" é 10/03 para o gasto diário. Teste na Tarefa 7.
3. **Fim de mês curto**: parcelamento iniciado em 31/01 vence em 28/02 e 31/03 (não 28/03). Teste na Tarefa 1.
4. **Dados de outro usuário**: toda edição/exclusão de registro alheio responde 404, inclusive endpoints JSON. Teste na Tarefa 12.
5. **Valores com 3 casas decimais**: o progresso de parcelas soma 66,666 e mostra o restante 33,334. Teste na Tarefa 2.

## Decisões em aberto (não fixar em teste até o Nelio decidir)

- **Centavo do parcelamento:** R$ 100 em 3× grava 3 × 33,333 = 99,999. A última parcela deveria absorver a diferença?
- **"Investimento" na tabela por categoria:** os gráficos do Resumo excluem a forma de pagamento "Investimento"; a tabela da aba Categorias inclui. Qual é a regra?
- **Barra de progresso do orçamento:** `overall_progress` divide o gasto nas categorias estimadas pelo total esperado (fixas + parcelas + estimativas). É isso que a barra deve mostrar?
- **Total esperado ajustado:** `adjusted_expected` soma o gasto avulso inteiro, inclusive o de categorias que já têm estimativa (R$ 100 estimados em Food + R$ 40 gastos em Food → conta 140). O gasto numa categoria estimada deveria contar de novo? (achado da revisão final)
- **Estimativa de R$ 0 com gasto:** hoje aparece com 0% e não como estourada. Deveria ficar vermelha? (achado da revisão final)

---

### Task 0: Helpers de teste compartilhados

**Files:**
- Create: `utils/tests/__init__.py`, `utils/tests/clock.py`
- Move: `reports/tests/html.py` → `utils/tests/html.py` (`git mv`)
- Modify: imports em `reports/tests/*.py` (`from reports.tests.html import …` → `from utils.tests.html import …`) e `reports/tests/test_recurring_payments.py` (remover `today_is` local, importar de `utils.tests.clock`)

**Interfaces:**
- Produces: `utils.tests.clock.today_is(day: date)` → context manager/decorator que faz `django.utils.timezone.now` devolver `day` às 12h no fuso do projeto; `utils.tests.clock.at(moment: datetime)` → idem para um instante exato (aware).
- Produces: `utils.tests.html.page`, `links_to`, `with_id`, `payment_checkboxes` (mesma assinatura de hoje).

- [ ] **Step 1:** mover os helpers e ajustar imports.
- [ ] **Step 2:** `DATABASE_URL= venv/bin/python manage.py test reports` → OK (78 testes).
- [ ] **Step 3:** commit `test: shared clock and HTML helpers in utils.tests`.

### Task 1: Fatura e parcelamento (modelos)

**Files:**
- Modify: `reports/tests/test_billing_month.py`
- Create: `registers/tests/test_installment_plan.py`

**Interfaces:** Consumes `Expense.objects.in_billing_month(year, month)`, `Installment.create_plan(...)` via POST em `register_expense`.

- [ ] **Step 1: Escrever os testes**

`test_billing_month.py`:
- `test_expense_without_payment_method_uses_the_calendar_month`: despesa de 01/03/2026 sem forma de pagamento está em `in_billing_month(2026, 3)` e não em `(2026, 2)`.

`test_installment_plan.py` (POST em `reverse('register_expense')` com `description='TV'`, `amount='100'`, `installments='3'`, `date='2026-01-31'`, categoria e forma de pagamento válidas):
- `test_creates_one_expense_per_month_with_numbered_descriptions`: descrições `['TV - 1/3', 'TV - 2/3', 'TV - 3/3']`, datas `[2026-01-31, 2026-02-28, 2026-03-31]`, todas do usuário logado e ligadas ao mesmo `Installment` com `total_amount=100`, `total_installments=3`.
- `test_each_installment_is_the_total_divided_by_the_count`: cada `amount == Decimal('33.333')`.
- `test_single_installment_creates_a_plain_expense`: `installments='1'` cria 1 `Expense` sem `installment_plan` e nenhum `Installment`.

- [ ] **Step 2:** rodar os dois módulos → PASS. Se falhar, reportar (não ajustar).
- [ ] **Step 3: Checar que o teste pega regressão:** trocar temporariamente `relativedelta(months=i)` por `timedelta(days=30*i)` em `Installment.create_plan`; o teste de datas deve falhar. Reverter.
- [ ] **Step 4:** commit `test: billing month without payment method and installment plans`.

### Task 2: Progresso das parcelas (`open_installments`)

**Files:** Create `reports/tests/test_installment_progress.py`

**Interfaces:** Consumes `reports.services.installments.open_installments(user, year, month) -> {'count', 'total_remaining', 'installments': [InstallmentProgress]}`.

- [ ] **Step 1: Escrever os testes** (plano "TV" da Tarefa 1 criado com `Installment.create_plan`, forma de pagamento com `start_billing_day=3`):
- `test_expenses_up_to_the_month_count_as_paid`: em `(2026, 2)` → `count == 1`, `paid_installments == 2`, `paid_amount == Decimal('66.666')`, `remaining_amount == Decimal('33.334')`, `progress_percentage == 66.7`.
- `test_plan_without_later_expenses_is_not_open`: em `(2026, 3)` → `count == 0`.
- `test_most_advanced_plans_come_first`: segundo plano "Sofá" de 4 parcelas a partir de 2026-02-01; em `(2026, 2)` a ordem é `['TV', 'Sofá']` (66,7% antes de 25%).
- `test_other_users_plans_are_ignored`: plano de outro usuário não aparece.
- `test_parcelas_tab_shows_remaining_in_reais`: GET `dashboard_installments?month=2&year=2026` contém `R$ 33,33`.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** trocar `Q(expenses__date__lte=end)` por `__lt` em `open_installments`; `test_expenses_up_to_the_month_count_as_paid` falha. Reverter.
- [ ] **Step 4:** commit `test: installment progress`.

### Task 3: Orçamento do mês (`monthly_budget`)

**Files:** Modify `reports/tests/test_monthly_budget.py`

**Interfaces:** Consumes `reports.services.budget.monthly_budget(user, year, month) -> BudgetSummary`.

- [ ] **Step 1: Escrever os testes** (cartão com `start_billing_day=3`):
- `test_regular_total_excludes_recurring_and_installment_expenses`: em maio/2026, avulsa 40 + parcela 100 + recorrente 50 → `total_regular == 40`.
- `test_totals_follow_the_bill_not_the_calendar`: avulsa em 02/06/2026 (antes do dia 3) entra em `monthly_budget(u, 2026, 5).total_regular`, não no de junho.
- `test_category_actual_and_over_budget_flag`: estimativa Food 100 e gasto Food 150 → item com `actual_amount == 150`, `progress_percentage == 150.0`, `is_over_budget is True`.
- `test_progress_is_capped_at_999`: estimativa 1, gasto 50 → `progress_percentage == 999.0`.
- `test_zero_estimate_has_zero_progress`: estimativa 0 → `progress_percentage == 0.0`, `is_over_budget is False`.
- `test_fixed_total_counts_only_schedules_due_that_month_with_iof`: recorrente internacional de 100 iniciando em 10/05/2026 → `total_fixed` em abril `== 0`, em maio `== Decimal('103.50')`; recorrente inativa não conta.
- `test_adjusted_expected_adds_spending_outside_the_plan`: `adjusted_expected == total_expected + total_regular`.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** em `monthly_budget`, trocar `.due_in(year, month).charged_total()` por soma de `total_amount` de todos os ativos; o teste de fixas falha. Reverter.
- [ ] **Step 4:** commit `test: monthly budget rules`.

### Task 4: Recorrentes que vencem no mês

**Files:** Create `reports/tests/test_recurring_due.py`

**Interfaces:** Consumes `RecurringExpense.objects.due_in(year, month)`, `.charged_total()`, `RecurringExpense.start_from(expense)`; páginas `recurring_expense_process`, `recurring_expense_list`, `expense_report`; endpoint `recurring_expense_toggle`.

- [ ] **Step 1: Escrever os testes** (recorrente "Spotify" internacional 100, início 10/05/2026):
- `test_processing_a_month_before_the_start_creates_nothing`: POST processar `month=4, year=2026` → nenhuma `Expense` do Spotify.
- `test_processing_the_start_month_creates_the_charged_amount`: `month=5` → 1 despesa em 2026-05-10, `amount == Decimal('103.50')`, `is_paid False`.
- `test_inactive_schedules_are_not_generated`: `generate_debit=False` → nada criado.
- `test_fixed_card_and_list_total_include_iof`: Resumo de maio/2026 mostra `R$ 103,50` no card de fixas; `/recurring-expenses/` mostra `R$ 103,50` no total ativo.
- `test_toggle_switches_generation_and_is_owner_only`: POST toggle → JSON `generate_debit False`, de novo → `True`; toggle de recorrente de outro usuário → 404 com JSON `error`.
- `test_recurring_from_expense_copies_description_amount_date_category_and_method`: POST `register_expense` com `is_recurring=on` → `RecurringExpense` com os mesmos 5 campos da despesa (complementa `test_recurring_expense_checkbox`, que só confere o vínculo).

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** remover `start_date__lte=...` de `due_in`; o teste do mês anterior ao início falha. Reverter.
- [ ] **Step 4:** commit `test: recurring expenses due in a month`.

### Task 5: Saldo global e gráficos do Resumo

**Files:** Create `reports/tests/test_global_balance.py`; Modify `reports/tests/test_yearly_charts.py`

**Interfaces:** Consumes `reports.services.summary.global_balance(user)`, `yearly_charts(user, year)`.

- [ ] **Step 1: Escrever os testes**
`test_global_balance.py` (com `today_is(date(2026, 3, 15))`):
- `test_balance_is_income_minus_expenses_up_to_the_end_of_this_month`: receita 1000 em 05/03, uma despesa de 616.999 em 10/03 e uma receita de 999 em 01/04 (mês seguinte, fora do saldo) → `global_balance == Decimal('383.001')` e o Resumo mostra `R$ 383,00`.
- `test_balance_ignores_other_users`.

`test_yearly_charts.py`:
- `test_investment_payment_method_is_left_out_of_spending`: despesa 500 com forma "Investimento" em mar/2026 não aparece nos datasets por forma de pagamento nem no total de despesas de março.
- `test_expenses_without_payment_method_have_their_own_series`: com `translation.override('en')`, existe um dataset `label == 'No Payment Method'`.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** apagar o filtro `!= INVESTMENT_PAYMENT_METHOD`; o teste de investimento falha. Reverter.
- [ ] **Step 4:** commit `test: global balance and investment exclusion`.

### Task 6: Tabela por categoria (aba Categorias)

**Files:** Create `reports/tests/test_category_table.py`

**Interfaces:** Consumes `reports.services.categories.category_month_table(user, year) -> {'categories': [{'name','id','months'}], 'totals'}`; página `dashboard_categories`.

- [ ] **Step 1: Escrever os testes**
- `test_amounts_go_to_the_billing_month`: despesa Food 10 em 02/06/2026 com `start_billing_day=3` cai em `months[4]` (maio).
- `test_categories_are_sorted_ignoring_case`: categorias "banco" e "Casa" → nomes `['banco', 'Casa']`.
- `test_totals_are_the_sum_of_each_month`: `totals[i] == sum(c['months'][i] for c in categories)` com valores fixos (ex.: Food 10 + Casa 5 em maio → `totals[4] == 15.0`).
- `test_uncategorized_expenses_have_a_row_without_link`: despesa sem categoria → linha `No Category` (em `en`) com `id None`; a página não tem link para `expense_list_page` nessa linha; as demais células com valor linkam `?category_id=<id>&month=<m>&year=<y>`.
- `test_other_users_are_ignored`.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** trocar `in_billing_year` por `filter(date__year=year)` no serviço; o teste do mês da fatura falha. Reverter.
- [ ] **Step 4:** commit `test: category month table`.

### Task 7: Gasto diário e média móvel

**Files:** Create `reports/tests/test_daily_spending.py`

**Interfaces:** Consumes `reports.services.daily.daily_spending(user, days, category=None) -> {'labels','dailyExpenses','movingAverages'}`; endpoint `daily_spending_data_ajax`.

- [ ] **Step 1: Escrever os testes**
- `test_series_covers_the_last_n_days_including_today`: com `today_is(date(2026, 3, 10))`, `days=7` → 8 labels de `'2026-03-03'` a `'2026-03-10'`, dias sem despesa com `0.0`.
- `test_moving_average_uses_seven_days_and_a_shorter_window_at_the_start`: despesa 14 em 03/03 → `movingAverages[0] == 14.0`, `movingAverages[1] == 7.0`; despesa 7 em 10/03 sozinha → último valor `1.0`.
- `test_category_filter_and_other_users`: só a categoria pedida; despesas de outro usuário ignoradas.
- `test_today_follows_sao_paulo_time`: com `at(datetime(2026, 3, 11, 2, 0, tzinfo=UTC))` o último label é `'2026-03-10'`.
- `test_ajax_accepts_only_the_offered_periods_and_expense_categories`: `days=5` → 400; `category_id` de categoria de receita → 400; `days=7` → 200 com as três chaves.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** mudar `MOVING_AVERAGE_WINDOW` para 5; o teste da média falha. Reverter.
- [ ] **Step 4:** commit `test: daily spending`.

### Task 8: Processador do CSV do Nubank

**Files:** Create `registers/tests/test_csv_processor.py`

**Interfaces:** Consumes `registers.csv.processor`: `detect_columns(df)`, `to_iso_date(value)`, `split_description(value)`, `process(df, columns)`, `to_csv_string(df)`; views `csv_processor`, `csv_processor_download`, `csv_processor_update_data`.

- [ ] **Step 1: Escrever os testes**
- `test_dates_go_from_brazilian_to_iso`: `'02/11/2024'`, `'02/11/2024 14:30'` → `'2024-11-02'`; `'2024-11-02'` fica igual; `''` → `''`.
- `test_description_splits_on_the_first_separator`: `'Uber - Trip - X'` → `('Uber', 'Trip - X')`; `'Pix'` → `('Pix', '')`; `None` → `('', '')`.
- `test_nubank_columns_are_found_exactly_by_case_or_by_part`: `['Data','Valor','Descrição']`; `['data','VALOR','descrição']`; `['Data da compra','Valor R$','Descricao']` → mapeamentos correspondentes; `['a']` → `None`.
- `test_unconvertible_dates_are_reported_by_row`: 1 data boa + 12 ruins → 4 colunas `['date','amount','payment_method','description']`; com `translation.override('en')` o aviso é `'Could not convert dates in 12 rows: 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 ... and 2 more'`.
- `test_missing_mapped_column_is_an_error`: mapeamento com coluna inexistente → `(None, [mensagem])`.
- `test_process_preview_edit_and_download`: POST `csv_processor` com texto Nubank → 200 com as linhas; POST JSON `{'rows': [...]}` em `csv_processor_update_data` → `success`; GET download devolve o CSV editado; corpo JSON que não é objeto (lista) → 400.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** trocar `partition(' - ')` por `rpartition(' - ')`; o teste de descrição falha. Reverter.
- [ ] **Step 4:** commit `test: Nubank CSV processor`.

### Task 9: Exportação de despesas

**Files:** Create `export/tests/__init__.py`, `export/tests/test_expense_export.py`

**Interfaces:** Consumes view `expense_export` (`/export/expense?month=&year=[&decimal_sep=][&download=1]`), `Expense.kind_label`.

- [ ] **Step 1: Escrever os testes**
- `test_csv_lists_the_calendar_month_of_the_logged_user`: despesa em 02/03/2026 com cartão `start_billing_day=3` entra em março (calendário, não fatura); despesa de outro usuário não entra; arquivo `despesas-2026-03.csv`.
- `test_kind_column_and_installment_wins_over_recurring`: com `translation.override('pt-br')`, colunas "Tipo" = `Parcela`, `Recorrente`, `Avulsa`; despesa com parcela **e** recorrente → `Parcela`.
- `test_decimal_separator`: `decimal_sep=,` → `12,50`; valor inválido (`;`) → `12.50`.
- `test_invalid_month_is_rejected`: `month=13` → 400.

- [ ] **Step 2:** rodar `DATABASE_URL= venv/bin/python manage.py test export` → PASS.
- [ ] **Step 3: Checar regressão:** inverter a ordem dos `if` em `Expense.kind`; o teste de tipo falha. Reverter.
- [ ] **Step 4:** commit `test: expense export`.

### Task 10: Estimativas de orçamento (formulário)

**Files:** Create `registers/tests/test_budget_estimate_form.py`

**Interfaces:** Consumes views `budget_estimate_list` (POST cria), `budget_estimate_update`.

- [ ] **Step 1: Escrever os testes**
- `test_duplicate_category_and_month_is_rejected_on_create`: segunda estimativa Food 11/2026 → página 200 com `An estimate already exists for this category this month.` (em `en`), 1 estimativa no banco.
- `test_editing_onto_an_existing_category_and_month_is_rejected`: editar Mercado→Food no mesmo mês → mesma mensagem, nada muda (antes era 500).
- `test_editing_an_estimate_keeps_its_own_slot`: editar só o valor → salva.
- `test_other_users_estimate_does_not_block`: outro usuário com Food 11/2026 não impede criar.
- `test_month_and_year_must_be_in_range`: `month=13` e `year=1999` → formulário inválido, nada criado.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** remover o `.exclude(pk=self.instance.pk)` do `clean()`; `test_editing_an_estimate_keeps_its_own_slot` falha. Reverter.
- [ ] **Step 4:** commit `test: budget estimate validation`.

### Task 11: Lançamento de despesas e receitas

**Files:** Create `registers/tests/test_expense_entry.py`

**Interfaces:** Consumes views `register_expense` (GET `?quick_fill=<id>`, POST), `register_income`.

- [ ] **Step 1: Escrever os testes**
- `test_quick_fill_prefills_the_form_from_an_active_own_preset`: preset ativo (descrição "Uber", valor 25, categoria, forma) → no formulário renderizado, `#id_description` vale `Uber`, `Decimal(#id_amount) == 25` e categoria/forma do preset estão selecionadas (ler com `utils.tests.html.page`).
- `test_quick_fill_ignores_zero_amount_and_other_users_or_inactive_presets`: valor 0 não preenche; preset inativo, de outro usuário ou `quick_fill=abc` → formulário vazio, 200.
- `test_expense_form_offers_only_expense_categories`: POST com categoria de receita → inválido, nada salvo.
- `test_description_is_limited_to_100_characters`: 101 caracteres → inválido.
- `test_income_accepts_comma_decimal_amounts`: POST `register_income` com `amount='12,50'` → receita com `Decimal('12.500')`.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** trocar o `amount` do `IncomeForm` pelo campo padrão do modelo; o teste da vírgula falha. Reverter.
- [ ] **Step 4:** commit `test: expense and income entry rules`.

### Task 12: Dados de outro usuário

**Files:** Create `registers/tests/test_ownership.py`

**Interfaces:** Consumes as URLs nomeadas abaixo.

- [ ] **Step 1: Escrever o teste** `test_other_users_records_are_not_found`, laço com `subTest` sobre registros do usuário B acessados pelo usuário A:
  - GET e POST `expense_update`, `recurring_expense_update`, `recurring_expense_expenses`, `budget_estimate_update`, `quick_fill_preset_edit` → 404, sem alteração no banco.
  - POST `delete_expense`, `delete_income`, `quick_fill_preset_delete`, `recurring_expense_delete`, `recurring_expense_toggle`, `recurring_expense_set_paid` → 404 com JSON contendo `error`; registro intacto.
  - POST `budget_estimate_delete` → 404, estimativa intacta.

- [ ] **Step 2:** rodar → PASS.
- [ ] **Step 3: Checar regressão:** remover `get_queryset` de `ExpenseUpdateView`; o subteste de `expense_update` falha. Reverter.
- [ ] **Step 4:** commit `test: other users' records are not found`.

### Task 13: Utilitários (`utils`)

**Files:** Create `utils/tests/test_dates_and_money.py`

**Interfaces:** Consumes `utils.money.format_brl`, filtro `{{ value|format_brl }}`, `utils.dates.parse_month_year(params, required=False) -> (year, month)`.

- [ ] **Step 1: Escrever os testes**
- `test_brl_format`: `Decimal('1234567.891')` → `'R$ 1.234.567,89'`; `Decimal('-1234.5')` → `'R$ -1.234,50'`; `0` → `'R$ 0,00'`.
- `test_brl_filter_is_blank_for_non_numbers`: `Template('{% load formatting %}{{ x|format_brl }}')` com `x` ausente ou `'abc'` → `''`.
- `test_month_year_defaults_to_today_and_returns_year_first`: com `today_is(date(2026, 11, 20))`, `{}` → `(2026, 11)`; `{'month': '3', 'year': '2025'}` → `(2025, 3)`.
- `test_month_year_rejects_missing_required_and_out_of_range`: `required=True` sem mês → `ValueError`; mês 13, ano 1999 e ano 2101 → `ValueError`.

- [ ] **Step 2:** `DATABASE_URL= venv/bin/python manage.py test utils` → PASS.
- [ ] **Step 3:** commit `test: money formatting and month/year parsing`.

### Fechamento

- [ ] `DATABASE_URL= venv/bin/python manage.py test` → tudo OK (179 de hoje + os novos).
- [ ] Atualizar `CLAUDE.md` (seção Testing Commands) com `utils` e `export` na lista de apps testados.
