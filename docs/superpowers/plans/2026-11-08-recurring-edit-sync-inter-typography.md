# Recorrentes: edição com sincronização, Inter, 3 casas decimais e escala de fontes — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar a fonte para Inter, reduzir a escala tipográfica (referência: GitLab), aceitar 3 casas decimais no valor da despesa, perguntar ao editar uma recorrente se o lançamento do mês também deve ser alterado e permitir editar o lançamento pelo pop-up de notificações, e tornar o campo de categoria (despesa e receita) totalmente navegável pelo teclado.

**Architecture:** Mudanças pequenas nas camadas que já existem (form field, service de recorrentes, view de edição, templates e CSS). Cada comportamento ganha um teste de interface com Playwright (Chromium) rodando contra `StaticLiveServerTestCase`, mais testes unitários onde a regra é de servidor.

**Tech Stack:** Django, Tailwind via CDN (config inline em `base.html` e `login.html`), Google Fonts, Playwright (Python) para testes de interface.

**Spec:** conversa de 2026-11-08 (sem documento de design; decisões listadas abaixo). Decisões minhas, não confirmadas pelo usuário, marcadas com **[call]**.

## Global Constraints

- Valor da despesa: aceitar até 3 casas decimais; se vierem mais, arredondar para 3 (`ROUND_HALF_UP`: `12.3456` → `12.346`).
- Fonte do app: **Inter** (peso variável 100–900) via Google Fonts; **Geist Mono** continua só para `.font-mono`. Dígitos tabulares no `body`.
- Escala tipográfica desktop (≥1024px), medida na tela do GitLab enviada (estimativa visual **[call]**): sidebar e texto padrão 14px, subtítulo 20px, título 28px, texto pequeno 12–13px.
- Mobile (<1024px): escala proporcional menor, `html` a 93,75% (texto padrão ≈13,1px, hoje 15px). Campos de formulário seguem com 16px no mobile para o iOS não dar zoom.
- Sincronização ao editar recorrente: só o lançamento do **mês atual** (`localdate()`), ligado por `Expense.reccurring_expense` (o campo tem o typo legado `reccurring`) **[call]**. Mapeamento de campos igual ao de `RecurringExpenseService.process_recurring_expenses_for_month` (valor lançado = `charged_amount`, com IOF). `is_paid` e `paid_at` não são alterados.
- Textos de interface novos em português, como as telas de notificação já existentes.
- Rodar testes com `source venv/bin/activate && python manage.py test <módulo>`.

## Review Focus

- Valor com vírgula/ponto e mais de 3 casas (`12,3456`) → salva `12.346`, sem erro de validação.
- Valor com 10 dígitos inteiros + 3 casas (limite de `max_digits=10`) → erro claro, não 500.
- Recorrente sem lançamento no mês atual → nenhuma pergunta aparece e o salvamento segue normal.
- Lançamento do mês já pago → sincronizar muda os dados mas mantém `is_paid`/`paid_at`.
- `start_date` com dia 31 e mês atual com 30 dias → o lançamento usa o último dia do mês, sem erro (o gerador de recorrentes hoje registra erro nesse caso; aqui clampa).
- `next` malicioso (`?next=https://evil.com`) na edição de despesa → ignorado, volta para `/`.
- Categoria: `Enter` no campo de busca sem nenhuma opção (lista vazia e campo vazio) → não envia o formulário nem dá erro de JS.
- Categoria: busca lenta (debounce de 300 ms) → `Enter` logo depois de digitar não escolhe uma opção da busca anterior; o JS deve esperar/cancelar a busca pendente antes de escolher.
- Categoria na receita: categorias de despesa e de receita com o mesmo nome não se misturam, e o formulário sem categoria continua mostrando o erro do Django.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `registers/tests/ui/__init__.py`, `registers/tests/ui/base.py` | Base de testes de interface (live server + Playwright + login) |
| `registers/forms.py` ou `registers/components/expense_form/expense_form_component.py` | Campo de valor com 3 casas e arredondamento |
| `reports/services/recurring_expense_service.py` | `sync_month_expense` |
| `reports/views.py` | `RecurringExpenseUpdateView` (contexto + sync), `ExpenseUpdateView` (`next`) |
| `reports/templates/reports/recurring_expense_update.html` | Diálogo de pergunta |
| `reports/templates/reports/components/payment_notification_row.html` | Botão de editar |
| `registers/static/js/category_autocomplete.js`, `registers/templates/register/components/category_autocomplete.html`, `registers/templates/register/income_form.html`, `registers/views.py` (endpoints de categoria) | Categoria navegável por teclado e disponível na receita |
| `registers/static/css/typography.css`, `registers/static/js/tailwind_config.js` | Inter, dígitos tabulares e escala |
| `registers/templates/core/base.html`, `registers/templates/auth/login.html` | Carregam o config único do Tailwind |

---

### Task 1: Base de testes de interface com Playwright

**Files:**
- Create: `registers/tests/ui/__init__.py`, `registers/tests/ui/base.py`, `registers/tests/ui/test_smoke.py`
- Modify: `requirements.txt` (adicionar `playwright`)

**Interfaces:**
- Produces: `class UITestCase(StaticLiveServerTestCase)` com `self.page` (Playwright `Page`), `self.login(user)` (faz login pela tela `/login` e espera sair dela) e `self.url(path) -> str`. Pula (`skipTest`) se `playwright` não estiver instalado. Define `DJANGO_ALLOW_ASYNC_UNSAFE=true` antes de abrir o navegador.

- [ ] **Step 1: Instalar** — `pip install playwright && playwright install chromium`; adicionar `playwright` ao `requirements.txt`.
- [ ] **Step 2: Escrever o teste** `test_smoke.UITestCase.test_login_reaches_dashboard`: cria usuário, chama `self.login(user)`, assert `self.page.url` termina com `/` e a página contém o texto "Meu Financeiro".
- [ ] **Step 3: Rodar e ver falhar** — `python manage.py test registers.tests.ui.test_smoke` → FAIL (`base` inexistente).
- [ ] **Step 4: Implementar `UITestCase`** em `base.py` (`setUpClass` abre Chromium headless, `tearDownClass` fecha; `setUp` cria um contexto/página novos). Descobrir a URL e os campos do login em `registers/templates/auth/login.html`.
- [ ] **Step 5: Rodar** o mesmo comando → PASS.
- [ ] **Step 6: Commit** — `git add registers/tests/ui requirements.txt && git commit -m "test: add Playwright UI test base"`

### Task 2: Valor com 3 casas decimais e arredondamento

**Files:**
- Modify: `registers/components/expense_form/expense_form_component.py:27`
- Test: `registers/tests/test_expense_amount_rounding.py`, `registers/tests/ui/test_expense_amount.py`

**Interfaces:**
- Produces: `class ThreePlacesDecimalField(forms.DecimalField)` em `registers/forms.py` (ou módulo próprio se o import circular atrapalhar), com `max_digits=10`, `decimal_places=3`, widget `NumberInput(attrs={'step': 'any'})` e `to_python` que quantiza para `Decimal('0.001')` com `ROUND_HALF_UP` antes da validação.

- [ ] **Step 1: Testes unitários** (`ExpenseForm` com `data` completo):
  - `test_three_decimals_accepted`: `'12.345'` → `form.is_valid()` e `cleaned_data['amount'] == Decimal('12.345')`
  - `test_more_than_three_decimals_rounds`: `'12.3456'` → `Decimal('12.346')`; `'12,3454'` (vírgula) → `Decimal('12.345')`
  - `test_too_many_integer_digits_is_error`: `'12345678.123'` → inválido, `'amount' in form.errors`
- [ ] **Step 2: Teste de interface** `test_edit_expense_accepts_four_decimals`: abre `/expense/<pk>/update/`, preenche `#id_amount` com `12.3456`, envia; assert que não há mensagem de erro e `Expense.amount == Decimal('12.346')`. Também assert `#id_amount` tem atributo `step="any"`.
- [ ] **Step 3: Rodar** `python manage.py test registers.tests.test_expense_amount_rounding registers.tests.ui.test_expense_amount` → FAIL.
- [ ] **Step 4: Implementar** `ThreePlacesDecimalField` e usá-lo em `get_form_fields` no lugar de `forms.DecimalField(... decimal_places=2)`.
- [ ] **Step 5: Rodar** os mesmos testes → PASS; rodar `python manage.py test registers` para ver que nada quebrou.
- [ ] **Step 6: Commit** — `fix: accept 3 decimal places on expense amount and round extra digits`

### Task 3: Sincronizar o lançamento do mês ao editar a recorrente

**Files:**
- Modify: `reports/services/recurring_expense_service.py`, `reports/views.py:937-953`, `reports/templates/reports/recurring_expense_update.html`
- Test: `reports/tests/test_recurring_sync.py`, `registers/tests/ui/test_recurring_edit_sync.py`

**Interfaces:**
- Produces: `RecurringExpenseService.sync_month_expense(recurring: RecurringExpense, today: date) -> Expense | None` — localiza o `Expense` com `reccurring_expense=recurring`, `date__year=today.year`, `date__month=today.month`; atualiza `description`, `amount=recurring.charged_amount`, `date` (dia de `start_date` limitado ao último dia do mês), `category`, `payment_method`; devolve o lançamento ou `None` se não existir. Não toca em `is_paid`/`paid_at`.
- Produces: contexto `month_expense` (lançamento do mês ou `None`) em `RecurringExpenseUpdateView`; campo POST `sync_month` (`'1'` sincroniza, qualquer outro valor não).

- [ ] **Step 1: Testes unitários** em `reports/tests/test_recurring_sync.py`:
  - `test_sync_updates_month_expense_fields`: recorrente de 100 → 150, lançamento do mês com 100; após `sync_month_expense(rec, date(2026,11,8))`, lançamento com `Decimal('150.000')`, nova descrição e categoria.
  - `test_sync_keeps_paid_state`: `is_paid=True, paid_at=date(2026,11,5)` permanecem.
  - `test_sync_clamps_day_31_in_30_day_month`: `start_date.day == 31`, `today` em novembro → data do lançamento `2026-11-30`.
  - `test_sync_returns_none_without_month_expense` e `test_sync_ignores_other_months`: lançamento de outubro não é tocado.
  - `test_sync_applies_iof_when_international`: valor lançado = `charged_amount`.
  - `test_update_view_sync_flag`: POST com `sync_month=1` altera o lançamento; POST com `sync_month=0` altera só o cadastro.
- [ ] **Step 2: Teste de interface** `test_recurring_edit_sync.py`:
  - `test_dialog_asks_and_syncs_both`: recorrente com lançamento no mês; abre a edição, muda o valor, clica "Atualizar"; assert que o diálogo `#sync-dialog` fica visível com os botões "Só o cadastro" e "Cadastro e lançamento do mês"; clica no segundo; assert que cadastro e lançamento têm o novo valor.
  - `test_dialog_only_registry`: mesmo fluxo clicando em "Só o cadastro" → lançamento mantém o valor antigo.
  - `test_no_dialog_without_month_expense`: sem lançamento no mês, o clique em "Atualizar" salva direto (nenhum `#sync-dialog` visível).
  - `test_no_dialog_when_nothing_changed`: sem alterar campos, salva direto.
- [ ] **Step 3: Rodar** `python manage.py test reports.tests.test_recurring_sync registers.tests.ui.test_recurring_edit_sync` → FAIL.
- [ ] **Step 4: Implementar** `sync_month_expense` no service; na view, `get_context_data` com `month_expense` e `form_valid` chamando o service quando `request.POST.get('sync_month') == '1'`, com a mensagem de sucesso indicando se o lançamento também foi atualizado.
- [ ] **Step 5: Template** — `<form data-has-month-expense="{{ month_expense|yesno:'true,false' }}">`, um `<input type="hidden" name="sync_month" value="0">` e um `<dialog id="sync-dialog">` com os dois botões. Script inline curto: no `submit`, se `has-month-expense` e algum campo diferir do `defaultValue`/`defaultChecked`, `preventDefault`, abre o diálogo; cada botão define `sync_month` e envia o formulário.
- [ ] **Step 6: Rodar** os testes → PASS.
- [ ] **Step 7: Commit** — `feat: ask to sync month expense when editing a recurring expense`

### Task 4: Botão de editar no pop-up de notificações

**Files:**
- Modify: `reports/templates/reports/components/payment_notification_row.html`, `reports/views.py:174-197` (`ExpenseUpdateView`)
- Test: `registers/tests/ui/test_notification_edit.py`, `reports/tests/test_expense_update_next.py`

**Interfaces:**
- Produces: `ExpenseUpdateView.get_success_url()` devolve o parâmetro `next` (GET na abertura, repassado por campo hidden no POST) quando `url_has_allowed_host_and_scheme(next, allowed_hosts={request.get_host()})`; senão `/`.

- [ ] **Step 1: Testes** — unitário: `test_next_param_is_used` (`/expense/<pk>/update/?next=/recurring-payments/` redireciona para lá) e `test_external_next_is_ignored` (`next=https://evil.com` → `/`). Interface: `test_notification_row_has_edit_button` — abre o dashboard, abre o pop-up, assert link "Editar" em cada linha com `href` contendo `/expense/<id>/update/`; clicar leva à edição, salvar volta para a página de origem.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** — link com ícone `fa-pen` e `aria-label="Editar {{ expense.description }}"` na linha, `?next={{ request.get_full_path|urlencode }}` (a linha é renderizada com `request=request`; no endpoint AJAX, `request.get_full_path` é o do endpoint, então passar `next_url` no contexto: o JS de `payment_notifications.js` já roda na página de origem, usar `location.pathname` e substituir o `next` no clique). Template de edição inclui `<input type="hidden" name="next">`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** — `feat: edit month expense from the payment notifications popup`

### Task 5: Categoria navegável por teclado (despesa e receita)

**Contexto:** hoje só o formulário de despesa usa o campo de categoria com busca ([category_autocomplete.html](registers/templates/register/components/category_autocomplete.html) + [category_autocomplete.js](registers/static/js/category_autocomplete.js)). O formulário de receita ([income_form.html:21](registers/templates/register/income_form.html#L21)) usa um `<select>` comum, e os endpoints `category_search_ajax` e `category_create_ajax` ([views.py:923](registers/views.py#L923)) filtram sempre por `type='expense'`. Então a tarefa inclui levar o mesmo componente para a receita.

**Files:**
- Modify: `registers/views.py:923-975` (endpoints aceitam `type`), `registers/templates/register/components/category_autocomplete.html`, `registers/static/js/category_autocomplete.js`, `registers/templates/register/income_form.html`
- Test: `registers/tests/test_category_ajax_type.py`, `registers/tests/ui/test_category_keyboard.py`

**Interfaces:**
- Produces: `GET /register/categories/search/?q=&type=expense|income` e `POST /register/categories/create/` com `{"name", "type"}`; `type` ausente ou inválido vira `expense` (compatível com o uso atual). O componente recebe `category_type` (`include ... with category_type="income"`) e expõe `data-category-type` no wrapper; o JS lê esse atributo e o envia nas duas chamadas.

**Comportamento do teclado** (decisão do usuário, detalhada **[call]** onde marcado):
- Ao abrir a lista, a primeira opção já vem destacada (`aria-selected="true"`, `role="option"`; a lista é `role="listbox"`). Isso vale também depois de cada busca (a lista é refeita ao digitar).
- `Enter` no campo de texto escolhe a opção destacada (não envia o formulário) e fecha a lista.
- `Tab` no campo vai para a primeira opção; `Tab` percorre as opções; `Tab` na última opção sai para o próximo campo do formulário e a lista fecha. `Shift+Tab` na primeira opção volta ao campo de texto; `Shift+Tab` no campo de texto vai para o campo anterior. Cada opção é focável (`tabindex="0"`), então a ordem é a natural do DOM e não precisa de interceptar `Tab`.
- `Enter` (e `Espaço`) numa opção focada escolhe essa opção e leva o foco ao **próximo campo do formulário**, para o fluxo continuar com `Tab` sem voltar ao campo de busca **[call]**.
- `ArrowDown`/`ArrowUp` movem o destaque entre as opções (extra barato, mesma lista) **[call]**; `Escape` fecha.
- A opção "Create ..." entra na mesma navegação e, se for a única, é a destacada.

- [ ] **Step 1: Testes de servidor** em `test_category_ajax_type.py`: `search?type=income` só devolve categorias `income`; sem `type` devolve `expense`; `create` com `type=income` cria categoria `income` e reutiliza uma existente de mesmo nome e tipo; `type=xyz` cai em `expense`.
- [ ] **Step 2: Testes de interface** em `test_category_keyboard.py` (despesa e receita, parametrizado pelo caminho `/register/expense` e `/register/income`; categorias "Mercado", "Moradia", "Mensalidade" criadas antes):
  - `test_first_option_is_highlighted`: foca o campo, digita `M`; a primeira opção ("Mensalidade", por ordem alfabética) tem `aria-selected="true"` e as demais `"false"`.
  - `test_enter_selects_first_option`: digita `Mo`, pressiona `Enter`; `#id_category` vale o id de "Moradia", o campo mostra "Moradia", a lista está oculta e o formulário **não** foi enviado.
  - `test_tab_walks_options_then_next_field`: digita `M`, `Tab` foca a opção 1, `Tab` a opção 2, `Tab` a opção 3, `Tab` foca o campo seguinte (valor/pagamento conforme o formulário); a lista está oculta.
  - `test_shift_tab_goes_back`: da opção 1, `Shift+Tab` devolve o foco ao campo de texto; do campo de texto, `Shift+Tab` foca o campo anterior do formulário.
  - `test_enter_on_focused_option_selects_and_moves_on`: `Tab` até a opção 2, `Enter`; categoria escolhida é a opção 2 e o foco está no campo seguinte.
  - `test_no_match_highlights_create_option`: digita `Zzz`; só existe "Create "Zzz"", destacada; `Enter` cria e seleciona a categoria (do tipo da página).
  - `test_income_page_lists_only_income_categories`: na receita, categorias de despesa não aparecem.
- [ ] **Step 3: Rodar** `python manage.py test registers.tests.test_category_ajax_type registers.tests.ui.test_category_keyboard` → FAIL.
- [ ] **Step 4: Implementar os endpoints** com um helper `_category_type(request_value) -> str` (`income` ou `expense`).
- [ ] **Step 5: Implementar o JS**: `renderDropdown` cria `li` com `role="option"`, `tabindex="0"`, `aria-selected`, destaca o primeiro (`highlightedIndex = 0`); `keydown` do campo trata `Enter` (escolhe o destacado), `ArrowDown/Up` e `Escape`; `keydown` da opção trata `Enter`/`Espaço` (escolhe e foca o próximo campo do formulário: o próximo elemento focável depois do wrapper) e setas; um `focusout` no wrapper fecha a lista quando o novo foco (`relatedTarget`) sai do wrapper. Ler o tipo de `data-category-type`.
- [ ] **Step 6: Receita**: trocar o `<select>` por `{% include "register/components/category_autocomplete.html" with category_type="income" %}` e carregar o script; passar `category_type="expense"` no formulário de despesa. Conferir que o `select` oculto (`#id_category`) continua dentro do formulário e que a validação de categoria obrigatória segue funcionando (envio sem categoria mostra o erro do Django).
- [ ] **Step 7: Rodar** os testes → PASS; `python manage.py test registers` sem regressões.
- [ ] **Step 8: Commit** — `feat: keyboard-navigable category autocomplete for expenses and incomes`

---

### Task 6: Inter e dígitos tabulares

**Files:**
- Modify: `registers/static/css/typography.css:1-6` e regra do `body`
- Test: `registers/tests/ui/test_typography.py`

- [ ] **Step 1: Teste de interface** `test_body_uses_inter_with_tabular_digits`: no dashboard, `getComputedStyle(document.body).fontFamily` começa com `Inter`, `fontVariantNumeric` contém `tabular-nums`, e `await document.fonts.load('14px Inter')` devolve ao menos uma fonte carregada.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** — `@import` do Google Fonts com `family=Inter:wght@100..900&family=Geist+Mono:wght@100..900`; `--font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif`; `body { font-variant-numeric: tabular-nums; }`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** — `feat: switch app font to Inter with tabular digits`

### Task 7: Escala tipográfica (GitLab)

**Files:**
- Create: `registers/static/js/tailwind_config.js` (config único do Tailwind, extraído dos dois templates)
- Modify: `registers/templates/core/base.html:16-31`, `registers/templates/auth/login.html` (mesmo bloco), `registers/static/css/typography.css:8-52`
- Test: `registers/tests/ui/test_typography.py` (acrescentar)

**Interfaces:**
- Produces: `tailwind.config.theme.extend.fontSize` com `xs 0.75rem/1rem`, `sm 0.8125rem/1.25rem`, `base 0.875rem/1.5rem`, `lg 1rem/1.5rem`, `xl 1.25rem/1.75rem`, `2xl 1.75rem/2.25rem`. `html` a 100% no desktop e 93,75% abaixo de 1024px.

- [ ] **Step 1: Testes de interface** (viewport 1280×800 e 390×800):
  - `test_desktop_scale_matches_reference`: `body` 14px; um elemento `.text-2xl` 28px; um `.text-xl` 20px; link da sidebar 14px.
  - `test_mobile_scale_is_smaller`: `body` entre 12px e 14px (exclusivo de 14); input de texto com 16px.
  - `test_login_uses_same_scale`: `/login` tem o mesmo `body` em 14px no desktop.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** — mover o `tailwind.config` para `tailwind_config.js` e carregá-lo logo depois do script do CDN nos dois templates; em `typography.css`, apagar o `html` a 112,5% e as sobrescritas `body .text-xs/.text-sm` (elas anulam a escala do Tailwind), `body { font-size: 0.875rem }`, `html { font-size: 93.75% }` com `@media (min-width: 1024px) { html { font-size: 100% } }`, inputs com `font-size: 16px` abaixo de 1024px e `0.875rem` a partir dele.
- [ ] **Step 4: Rodar** → PASS; abrir as telas principais (`/`, recorrentes, edição, login) com o MCP do Playwright e conferir que nada estourou nem ficou ilegível.
- [ ] **Step 5: Commit** — `style: reduce typography scale to GitLab proportions`

### Task 8: Demonstração e verificação final

- [ ] **Step 1:** `python manage.py test` completo → tudo passando (reportar falhas reais, se houver).
- [ ] **Step 2:** `python manage.py runserver` e, com o MCP do Playwright, percorrer: editar despesa com `12.3456`; editar recorrente com o diálogo nas duas respostas; botão "Editar" no pop-up; cadastrar despesa e receita só com o teclado (digitar na categoria, `Enter`, `Tab`, `Shift+Tab`); telas em 1280px e 390px. Salvar capturas de tela no scratchpad e mostrá-las ao usuário.

---

## Self-Review

- Cobertura: categoria por teclado em despesa e receita (T5), Inter (T6), escala GitLab desktop+mobile (T7), 3 casas e arredondamento (T2), pergunta ao editar recorrente (T3), botão de editar no pop-up (T4), testes de interface (T1 + cada tarefa), demonstração (T8).
- Riscos conhecidos: os testes de fonte e de escala dependem do CDN do Tailwind e do Google Fonts (precisam de internet); as medidas do GitLab são estimativas da captura de tela.
- Tarefas independentes entre si depois da T1; T6 e T7 mexem no mesmo `typography.css`, então executar em ordem.
