# Resumo e Gastos sem scroll no desktop — Plano

> **Para agentes:** use superpowers:executing-plans. Passos com checkbox.

**Goal:** Trazer o gráfico "despesas por forma de pagamento" de volta ao Resumo (ao lado de receita × despesa) e fazer Resumo e Gastos caberem na altura da tela no desktop (≥ lg), sem scroll da página.

**Architecture:** `_layout.html` ganha um bloco `fit_screen`. Quando uma aba o ativa, o `<article>` vira coluna de altura `100dvh - 3rem` (o `main` tem `lg:p-6`) e a área de conteúdo vira `flex-1 min-h-0`. Os cards de gráfico usam `relative flex-1 min-h-0` no contêiner do `<canvas>` (Chart.js com `maintainAspectRatio:false`). Mobile não muda (scroll normal + barra inferior).

**Tech Stack:** Django templates, Tailwind CDN, Chart.js, Playwright (verificação visual).

## Global Constraints
- Breakpoint desktop = Tailwind `lg` (1024px). Abaixo disso nada muda.
- Só Resumo e Gastos são "fit screen". Categorias, Parcelas, Despesas continuam com scroll.
- Sem novas dependências. Sem JS novo para layout (só CSS).

## Review Focus
- Viewport 1280×720 (notebook): Resumo ainda cabe? Cards de resumo quebram em 2 linhas e empurram o gráfico.
- Mês sem dados (listas vazias): cards e gráficos não podem colapsar a altura a 0.
- Orçamento com muitas categorias: o card rola por dentro, não a página.
- Mobile 390px: sem overflow horizontal; gráficos com altura > 0.
- Categorias não pode mais renderizar o gráfico de forma de pagamento (canvas duplicado).

---

### Task 1: Gráfico de forma de pagamento volta ao Resumo

**Files:**
- Modify: `reports/views/dashboard.py` (`expense_report`, `categories`)
- Modify: `reports/templates/reports/tabs/resumo.html`, `tabs/categorias.html`
- Test: `reports/tests/test_dashboard_tabs.py`

**Interfaces:**
- Produces: contexto do Resumo passa a ter `calculated_monthy_payment_method_expense_totals` e `monthly_expense_income_datasets`, vindos de uma única chamada a `get_optimized_payment_method_data()`.

- [ ] **Step 1: testes que falham** em `DashboardTabsTest`:
  `test_home_has_both_charts` → GET `expense_report` contém `id="expenseIncomeTotalChart"` e `id="calculatedPaymentMethodExpenseChart"`;
  `test_categories_has_no_payment_chart` → GET `dashboard_categories` não contém `calculatedPaymentMethodExpenseChart`.
- [ ] **Step 2:** rodar `DATABASE_URL= python manage.py test reports.tests.test_dashboard_tabs` → 2 falhas.
- [ ] **Step 3:** em `expense_report`, chamar `get_optimized_payment_method_data()` uma vez e usar `['combined_datasets']` e `['datasets']`; em `categories`, remover a chave e a chamada; `resumo.html` inclui `payment_method_chart.html`; `categorias.html` deixa de incluí-lo.
- [ ] **Step 4:** rodar o mesmo comando → passa.
- [ ] **Step 5:** commit `feat: payment method chart back on resumo`.

### Task 2: Layout "fit screen" no desktop (Resumo e Gastos)

**Files:**
- Modify: `tabs/_layout.html`, `tabs/resumo.html`, `tabs/gastos.html`
- Modify: `components/{expense_income_chart,payment_method_chart,budget_estimate_card,daily_spending_chart,summary_cards}.html`
- Test: `scripts/check_layout.mjs` não existe; verificação via Playwright (Task 3).

**Interfaces:**
- `_layout.html` expõe `{% block fit_screen %}{% endblock %}`; quando o filho define `{% block fit_screen %}1{% endblock %}`, aplica `lg:h-[calc(100dvh-3rem)] lg:flex lg:flex-col` no article e `lg:flex-1 lg:min-h-0` na section.

- [ ] **Step 1:** `_layout.html`: classes condicionais usando `{% block fit_screen %}{% endblock as fit %}` não existe em Django → usar variável de contexto `fit_screen` (True) passada pelas views `expense_report` e `spending`.
- [ ] **Step 2:** `resumo.html`: em `lg`, grade 3 colunas `lg:grid-cols-3 lg:grid-rows-1`, cada filho `min-h-0`: orçamento (rola por dentro: `overflow-y-auto`), receita × despesa, forma de pagamento. Cards de resumo ficam acima, altura natural.
- [ ] **Step 3:** componentes de gráfico: card `flex flex-col lg:min-h-0 lg:h-full`; contêiner do canvas `relative h-[70vh] min-h-[360px] lg:h-auto lg:min-h-0 lg:flex-1`.
- [ ] **Step 4:** `gastos.html`/`daily_spending_chart.html`: card `lg:h-full flex flex-col`, contêiner do canvas `lg:flex-1 lg:min-h-0 relative`, removendo `lg:min-h-[600px]`.
- [ ] **Step 5:** commit `feat: resumo and gastos fit the desktop viewport`.

### Task 3: Verificação (integração + regressão)

- [ ] **Step 1 (regressão backend):** `DATABASE_URL= python manage.py test --noinput` → todos OK.
- [ ] **Step 2 (integração visual, Playwright, servidor local com cópia do banco):**
  | Viewport | Aba | Esperado |
  |---|---|---|
  | 1440×900 | resumo, gastos | `scrollHeight <= innerHeight`, canvases com altura > 200px |
  | 1280×720 | resumo, gastos | idem |
  | 1440×900 | categorias, parcelas, despesas | sem erros JS; scroll permitido |
  | 390×844 | todas | `scrollWidth <= innerWidth`; barra de abas visível; gráficos > 0px |
  | 1440×900 | resumo com mês sem dados | sem erro, cards visíveis |
- [ ] **Step 3:** erros de console = 0 em todas as páginas.
- [ ] **Step 4:** commit de ajustes + push na branch.
