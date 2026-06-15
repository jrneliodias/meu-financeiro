# Installment Monthly Card — AJAX Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar o card "Monthly Installments:" em um portal clicável que abre um modal AJAX listando todas as expenses de parcelas do mês selecionado.

**Architecture:** Um novo método no `InstallmentRepository` busca as expenses de parcelas do mês com select_related. Uma nova view AJAX em `reports/views.py` expõe esses dados como JSON, seguindo o padrão dos endpoints `expense_details_ajax` e `recurring_expense_details_ajax`. O card `installment_monthly_card.html` ganha um botão info + modal com fetch JS inline.

**Tech Stack:** Django 5.x, Python 3.10, Tailwind CSS, Vanilla JS (fetch API), Django i18n, FontAwesome icons.

---

## File Map

| Arquivo | Mudança |
|---|---|
| `reports/tests/test_installment_monthly_summary.py` | Adicionar testes para novo método de repositório e nova view |
| `reports/repository/installment_repository.py` | Adicionar `get_monthly_installment_expenses_detail()` |
| `reports/views.py` | Adicionar `installment_expenses_ajax` view |
| `reports/urls.py` | Registrar nova URL `installment-expenses-ajax/` |
| `reports/templates/reports/components/installment_monthly_card.html` | Adicionar botão info, modal markup, JS fetch |
| `locale/en/LC_MESSAGES/django.po` | Adicionar strings i18n |
| `locale/pt_BR/LC_MESSAGES/django.po` | Adicionar strings i18n |
| `locale/en/LC_MESSAGES/django.mo` | Recompilar |
| `locale/pt_BR/LC_MESSAGES/django.mo` | Recompilar |

---

## Task 1: Teste do método de repositório

**Files:**
- Modify: `reports/tests/test_installment_monthly_summary.py`

- [ ] **Step 1: Adicionar os testes para o novo método**

Abra `reports/tests/test_installment_monthly_summary.py`. Ao final do arquivo, adicione a nova classe de teste abaixo. Use o mesmo `setUp` base como referência — a classe nova define o seu próprio `setUp` completo:

```python
class GetMonthlyInstallmentExpensesDetailTest(TestCase):
    """Tests para InstallmentRepository.get_monthly_installment_expenses_detail."""

    def setUp(self):
        self.user = User.objects.create_user(username='detailuser', password='pass')
        self.category = Category.objects.create(name='Eletronicos', type='expense')
        self.payment_method = PaymentMethod.objects.create(
            name='Nubank', start_billing_day=10
        )
        self.installment = Installment.objects.create(
            user=self.user,
            description='iPhone 15',
            total_amount=Decimal('6000.00'),
            total_installments=12,
            start_date=date(2026, 1, 1),
            category=self.category,
            payment_method=self.payment_method,
        )
        self.expense = Expense.objects.create(
            user=self.user,
            description='iPhone 15 3/12',
            amount=Decimal('500.00'),
            date=date(2026, 6, 15),
            category=self.category,
            payment_method=self.payment_method,
            installment_plan=self.installment,
        )
        self.repo = InstallmentRepository()

    def test_retorna_expenses_de_parcelas_do_mes(self):
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['description'], 'iPhone 15 3/12')
        self.assertEqual(result[0]['installment_plan__description'], 'iPhone 15')

    def test_exclui_outros_meses(self):
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=5, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 0)

    def test_exclui_expenses_sem_parcela(self):
        Expense.objects.create(
            user=self.user,
            description='Almoço avulso',
            amount=Decimal('50.00'),
            date=date(2026, 6, 10),
            installment_plan=None,
        )
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 1)

    def test_exclui_expenses_de_outro_usuario(self):
        other_user = User.objects.create_user(username='outro', password='pass')
        other_installment = Installment.objects.create(
            user=other_user,
            description='TV',
            total_amount=Decimal('1200.00'),
            total_installments=6,
            start_date=date(2026, 1, 1),
        )
        Expense.objects.create(
            user=other_user,
            description='TV 1/6',
            amount=Decimal('200.00'),
            date=date(2026, 6, 10),
            installment_plan=other_installment,
        )
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 1)

    def test_ordena_por_amount_decrescente(self):
        Expense.objects.create(
            user=self.user,
            description='iPhone 15 4/12',
            amount=Decimal('800.00'),
            date=date(2026, 6, 20),
            installment_plan=self.installment,
        )
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 2)
        self.assertGreaterEqual(result[0]['amount'], result[1]['amount'])

    def test_retorna_campos_obrigatorios(self):
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        row = result[0]
        for field in ('id', 'description', 'amount', 'date',
                      'category__name', 'payment_method__name',
                      'installment_plan__description'):
            self.assertIn(field, row)
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

```bash
python manage.py test reports.tests.test_installment_monthly_summary.GetMonthlyInstallmentExpensesDetailTest -v 2
```

Resultado esperado: `AttributeError: 'InstallmentRepository' object has no attribute 'get_monthly_installment_expenses_detail'`

---

## Task 2: Implementação do método de repositório

**Files:**
- Modify: `reports/repository/installment_repository.py`

- [ ] **Step 1: Adicionar o método ao InstallmentRepository**

Abra `reports/repository/installment_repository.py`. Adicione o método abaixo após `get_monthly_installment_expenses_total`:

```python
def get_monthly_installment_expenses_detail(
    self,
    month: int,
    year: int,
    user=None,
):
    """
    Retorna as expenses individuais de parcelas do mês/ano especificado.

    Usado pelo endpoint AJAX do modal do installment_monthly_card.
    Retorna valores via .values() para serialização direta em JSON.
    """
    queryset = Expense.objects.filter(
        date__month=month,
        date__year=year,
        installment_plan__isnull=False,
    ).select_related('category', 'payment_method', 'installment_plan')

    if user:
        queryset = queryset.filter(user=user)

    return queryset.values(
        'id',
        'description',
        'amount',
        'date',
        'category__name',
        'payment_method__name',
        'installment_plan__description',
    ).order_by('-amount', 'description')
```

- [ ] **Step 2: Rodar os testes e confirmar que passam**

```bash
python manage.py test reports.tests.test_installment_monthly_summary.GetMonthlyInstallmentExpensesDetailTest -v 2
```

Resultado esperado: `OK` com todos os testes verdes.

- [ ] **Step 3: Commit**

```bash
git add reports/repository/installment_repository.py reports/tests/test_installment_monthly_summary.py
git commit -m "feat: add get_monthly_installment_expenses_detail to InstallmentRepository"
```

---

## Task 3: Testes da view AJAX

**Files:**
- Modify: `reports/tests/test_installment_monthly_summary.py`

- [ ] **Step 1: Adicionar imports necessários no topo do arquivo de testes**

Verifique se os imports a seguir já estão presentes no topo de `reports/tests/test_installment_monthly_summary.py`. Adicione apenas os que faltam:

```python
from django.test import TestCase, Client
from django.urls import reverse
```

Os imports de `User`, `Category`, `Expense`, `Installment`, `PaymentMethod`, `Decimal`, `date` já existem no arquivo — não duplique.

- [ ] **Step 2: Adicionar a classe de testes da view**

Ao final do arquivo, adicione:

```python
class InstallmentExpensesAjaxViewTest(TestCase):
    """Testes para a view installment_expenses_ajax."""

    def setUp(self):
        self.user = User.objects.create_user(username='viewuser', password='pass')
        self.client = Client()
        self.client.login(username='viewuser', password='pass')
        self.url = reverse('installment_expenses_ajax')
        self.ajax_header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        category = Category.objects.create(name='Tech', type='expense')
        payment_method = PaymentMethod.objects.create(name='Visa', start_billing_day=5)
        installment = Installment.objects.create(
            user=self.user,
            description='MacBook',
            total_amount=Decimal('12000.00'),
            total_installments=12,
            start_date=date(2026, 1, 1),
            category=category,
            payment_method=payment_method,
        )
        self.expense = Expense.objects.create(
            user=self.user,
            description='MacBook 6/12',
            amount=Decimal('1000.00'),
            date=date(2026, 6, 10),
            category=category,
            payment_method=payment_method,
            installment_plan=installment,
        )

    def test_requer_header_ajax(self):
        response = self.client.get(self.url, {'month': '6', 'year': '2026'})
        self.assertEqual(response.status_code, 400)

    def test_requer_login(self):
        self.client.logout()
        response = self.client.get(self.url, {'month': '6', 'year': '2026'}, **self.ajax_header)
        self.assertEqual(response.status_code, 302)

    def test_retorna_400_sem_month(self):
        response = self.client.get(self.url, {'year': '2026'}, **self.ajax_header)
        self.assertEqual(response.status_code, 400)

    def test_retorna_400_sem_year(self):
        response = self.client.get(self.url, {'month': '6'}, **self.ajax_header)
        self.assertEqual(response.status_code, 400)

    def test_retorna_400_com_month_invalido(self):
        response = self.client.get(self.url, {'month': 'abc', 'year': '2026'}, **self.ajax_header)
        self.assertEqual(response.status_code, 400)

    def test_retorna_200_com_params_validos(self):
        response = self.client.get(self.url, {'month': '6', 'year': '2026'}, **self.ajax_header)
        self.assertEqual(response.status_code, 200)

    def test_resposta_contem_campos_obrigatorios(self):
        response = self.client.get(self.url, {'month': '6', 'year': '2026'}, **self.ajax_header)
        data = response.json()
        self.assertIn('expenses', data)
        self.assertIn('total_amount', data)
        self.assertIn('count', data)

    def test_lista_apenas_expenses_do_usuario(self):
        response = self.client.get(self.url, {'month': '6', 'year': '2026'}, **self.ajax_header)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['expenses'][0]['description'], 'MacBook 6/12')

    def test_total_amount_corresponde_a_soma(self):
        response = self.client.get(self.url, {'month': '6', 'year': '2026'}, **self.ajax_header)
        data = response.json()
        self.assertAlmostEqual(data['total_amount'], 1000.0)

    def test_cada_expense_tem_campos_obrigatorios(self):
        response = self.client.get(self.url, {'month': '6', 'year': '2026'}, **self.ajax_header)
        expense = response.json()['expenses'][0]
        for field in ('description', 'amount', 'date', 'category', 'payment_method', 'installment_plan'):
            self.assertIn(field, expense)
```

- [ ] **Step 3: Rodar os testes e confirmar que falham**

```bash
python manage.py test reports.tests.test_installment_monthly_summary.InstallmentExpensesAjaxViewTest -v 2
```

Resultado esperado: `NoReverseMatch` ou `ImportError` — a view ainda não existe.

---

## Task 4: Implementação da view AJAX

**Files:**
- Modify: `reports/views.py`
- Modify: `reports/urls.py`

- [ ] **Step 1: Adicionar a view em reports/views.py**

Abra `reports/views.py`. Adicione a função abaixo **antes** da linha `def index(request):` ou após o bloco de imports, logo após a última view existente (`process_recurring_expenses_ajax`). Use o mesmo padrão de `expense_details_ajax`:

```python
@login_required
def installment_expenses_ajax(request):
    """
    AJAX endpoint para listar as expenses de parcelas do mês selecionado.

    Retorna as expenses individuais que compõem o total exibido no
    installment_monthly_card, permitindo ao usuário verificar o detalhamento.

    Query Parameters:
        month: int (1-12)
        year: int (ex: 2026)

    Returns:
        JsonResponse com:
        - expenses: lista de expenses de parcelas
        - total_amount: soma dos valores
        - count: quantidade de expenses
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': _('Invalid request')}, status=400)

    month_str = request.GET.get('month', '').strip()
    year_str = request.GET.get('year', '').strip()

    if not month_str or not year_str:
        return JsonResponse({'error': _('month and year are required')}, status=400)

    try:
        month = int(month_str)
        year = int(year_str)
    except ValueError:
        return JsonResponse({'error': _('month and year must be integers')}, status=400)

    try:
        from reports.repository.installment_repository import InstallmentRepository
        repo = InstallmentRepository()
        expenses_qs = repo.get_monthly_installment_expenses_detail(
            month=month, year=year, user=request.user
        )

        expenses_list = []
        total_amount = Decimal('0.00')

        for expense in expenses_qs:
            total_amount += expense['amount']
            expenses_list.append({
                'description': expense['description'],
                'amount': float(expense['amount']),
                'date': expense['date'].isoformat(),
                'category': expense['category__name'] or _('Uncategorized'),
                'payment_method': expense['payment_method__name'] or _('N/A'),
                'installment_plan': expense['installment_plan__description'] or '',
            })

        return JsonResponse({
            'month': month,
            'year': year,
            'expenses': expenses_list,
            'total_amount': float(total_amount),
            'count': len(expenses_list),
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error fetching installment expenses: {e}', exc_info=True)
        return JsonResponse({'error': _('An unexpected error occurred')}, status=500)
```

**Atenção:** O import de `InstallmentRepository` vai **dentro do bloco `try`** da view, seguindo exatamente o padrão de `expense_details_ajax` que faz `from reports.repository.expense_repository import ExpenseRepository` dentro do try. Não adicione no topo do arquivo.

- [ ] **Step 2: Registrar a URL em reports/urls.py**

Abra `reports/urls.py`. Adicione a linha ao final de `urlpatterns`:

```python
path("installment-expenses-ajax/", views.installment_expenses_ajax, name="installment_expenses_ajax"),
```

- [ ] **Step 3: Rodar os testes e confirmar que passam**

```bash
python manage.py test reports.tests.test_installment_monthly_summary.InstallmentExpensesAjaxViewTest -v 2
```

Resultado esperado: `OK` com todos os testes verdes.

- [ ] **Step 4: Rodar todos os testes do app para garantir sem regressões**

```bash
python manage.py test reports -v 2
```

Resultado esperado: todos os testes passam.

- [ ] **Step 5: Commit**

```bash
git add reports/views.py reports/urls.py reports/tests/test_installment_monthly_summary.py
git commit -m "feat: add installment_expenses_ajax AJAX endpoint"
```

---

## Task 5: Strings de internacionalização

**Files:**
- Modify: `locale/en/LC_MESSAGES/django.po`
- Modify: `locale/pt_BR/LC_MESSAGES/django.po`

- [ ] **Step 1: Adicionar strings em en/django.po**

Abra `locale/en/LC_MESSAGES/django.po`. Localize o bloco de entradas existentes e adicione ao final (antes da última linha em branco, se houver):

```po
msgid "Installment Expenses"
msgstr "Installment Expenses"

msgid "No installment expenses found for this period."
msgstr "No installment expenses found for this period."

msgid "Installment Plan"
msgstr "Installment Plan"
```

- [ ] **Step 2: Adicionar strings em pt_BR/django.po**

Abra `locale/pt_BR/LC_MESSAGES/django.po`. Adicione ao final:

```po
msgid "Installment Expenses"
msgstr "Despesas de Parcelas"

msgid "No installment expenses found for this period."
msgstr "Nenhuma despesa de parcela encontrada para este período."

msgid "Installment Plan"
msgstr "Plano de Parcelas"
```

- [ ] **Step 3: Compilar os arquivos de tradução**

```bash
python manage.py compilemessages
```

Resultado esperado: arquivos `.mo` atualizados sem erros.

- [ ] **Step 4: Commit**

```bash
git add locale/
git commit -m "i18n: add translation strings for installment expenses modal"
```

---

## Task 6: Template — botão info, modal e JS fetch

**Files:**
- Modify: `reports/templates/reports/components/installment_monthly_card.html`

- [ ] **Step 1: Substituir o conteúdo do template**

O card atual exibe apenas o total sem interatividade. Substitua o conteúdo completo de `reports/templates/reports/components/installment_monthly_card.html` por:

```html
{% load i18n %}
<div
  class="bg-zinc-800/40 p-3 md:p-4 py-2 rounded-lg"
  data-month="{{ selected_month }}"
  data-year="{{ selected_year }}"
  id="installmentMonthlyCardRoot"
>
  <div class="flex flex-col items-start">
    <div class="flex items-center gap-1">
      <p class="text-white text-xs md:text-sm">{% trans "Monthly Installments:" %}</p>
      <button
        type="button"
        id="installmentExpensesBtn"
        class="text-zinc-500 hover:text-zinc-300 transition-colors"
        title="{% trans 'See installment expenses' %}"
      >
        <i class="fas fa-info-circle text-xs"></i>
      </button>
    </div>
    <span id="installmentMonthlyDisplay" class="text-purple-400 text-xl md:text-2xl font-bold">
      {{ installment_monthly_summary.formatted_total }}
    </span>
  </div>
</div>

<!-- Installment Expenses Modal -->
<div
  id="installmentExpensesModal"
  class="hidden fixed inset-0 bg-black/60 flex items-center justify-center z-50"
  onclick="if(event.target===this) this.classList.add('hidden')"
>
  <div class="bg-zinc-800 rounded-xl shadow-xl p-6 w-96 max-w-[90vw] max-h-[80vh] flex flex-col">
    <div class="flex items-center justify-between mb-4 flex-shrink-0">
      <h3 class="text-white font-semibold text-base">{% trans "Installment Expenses" %}</h3>
      <button
        type="button"
        id="installmentExpensesModalClose"
        class="text-zinc-400 hover:text-white transition-colors"
      >
        <i class="fas fa-times"></i>
      </button>
    </div>

    <div id="installmentExpensesList" class="overflow-y-auto flex-1 space-y-2">
      <!-- Preenchido via JS -->
    </div>

    <div id="installmentExpensesFooter" class="hidden border-t border-zinc-700 pt-3 mt-3 flex-shrink-0 flex justify-between items-center">
      <span class="text-zinc-400 text-sm font-medium">{% trans "Total" %}</span>
      <span id="installmentExpensesTotal" class="text-purple-400 font-bold text-base"></span>
    </div>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function () {
  // Formatar valor para BRL usando Intl.NumberFormat
  const formatBRL = (value) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);

  // Formatar data ISO para DD/MM/YYYY
  const formatDate = (isoDate) => {
    const [y, m, d] = isoDate.split('-');
    return `${d}/${m}/${y}`;
  };

  // Atualizar display do total via JS para formatação pt-BR
  const rawValue = {{ installment_monthly_summary.total_amount|default:0 }};
  document.getElementById('installmentMonthlyDisplay').textContent = formatBRL(rawValue);

  const modal = document.getElementById('installmentExpensesModal');
  const list = document.getElementById('installmentExpensesList');
  const footer = document.getElementById('installmentExpensesFooter');
  const totalEl = document.getElementById('installmentExpensesTotal');
  const root = document.getElementById('installmentMonthlyCardRoot');

  // Fechar modal
  document.getElementById('installmentExpensesModalClose').addEventListener('click', () => {
    modal.classList.add('hidden');
  });

  // Abrir modal e carregar dados
  document.getElementById('installmentExpensesBtn').addEventListener('click', () => {
    const month = root.dataset.month;
    const year = root.dataset.year;

    modal.classList.remove('hidden');
    footer.classList.add('hidden');
    list.innerHTML = '<div class="text-center text-zinc-400 py-4"><i class="fas fa-spinner fa-spin mr-2"></i>{% trans "Loading..." %}</div>';

    fetch(`/installment-expenses-ajax/?month=${month}&year=${year}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then((res) => {
        if (!res.ok) throw new Error('Request failed');
        return res.json();
      })
      .then((data) => {
        if (data.count === 0) {
          list.innerHTML = '<p class="text-zinc-400 text-sm text-center py-4">{% trans "No installment expenses found for this period." %}</p>';
          return;
        }

        list.innerHTML = data.expenses.map((exp) => `
          <div class="bg-zinc-700/50 rounded-lg p-3">
            <div class="flex justify-between items-start gap-2">
              <p class="text-white text-sm font-medium truncate flex-1">${exp.description}</p>
              <span class="text-purple-400 font-semibold text-sm flex-shrink-0">${formatBRL(exp.amount)}</span>
            </div>
            <div class="flex flex-wrap gap-1 mt-1">
              <span class="text-zinc-400 text-xs">${formatDate(exp.date)}</span>
              ${exp.category ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-600 text-gray-300">${exp.category}</span>` : ''}
              ${exp.payment_method ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-900/50 text-blue-300">${exp.payment_method}</span>` : ''}
            </div>
            ${exp.installment_plan ? `<p class="text-zinc-500 text-xs mt-1">{% trans "Installment Plan" %}: ${exp.installment_plan}</p>` : ''}
          </div>
        `).join('');

        totalEl.textContent = formatBRL(data.total_amount);
        footer.classList.remove('hidden');
      })
      .catch(() => {
        list.innerHTML = '<p class="text-red-400 text-sm text-center py-4">{% trans "An unexpected error occurred" %}</p>';
      });
  });
});
</script>
```

**Notas importantes:**
- `{{ selected_month }}` e `{{ selected_year }}` estão disponíveis no contexto porque o card é incluído dentro de `filter_form.html`, que por sua vez é incluído no `expense_report.html` cujo contexto já contém ambas as variáveis.
- O `fetch` usa URL hardcoded `/installment-expenses-ajax/` para evitar dependência de `{% url %}` dentro de template strings JS. Compatível com o padrão existente no projeto.

- [ ] **Step 2: Verificar o servidor**

```bash
source venv/bin/activate && python manage.py runserver
```

Acesse `http://localhost:8000/` no browser. Verifique:
1. O card "Monthly Installments:" exibe o valor formatado em BRL.
2. O ícone `ⓘ` aparece ao lado do label.
3. Ao clicar no ícone, o modal abre com o spinner.
4. O modal popula com a lista de expenses (ou mensagem de "nenhuma encontrada").
5. O total no footer bate com o valor do card.
6. Fechar o modal funciona pelo `×` e pelo clique no overlay.

- [ ] **Step 3: Commit**

```bash
git add reports/templates/reports/components/installment_monthly_card.html
git commit -m "feat: transform installment monthly card into AJAX modal portal"
```

---

## Task 7: Verificação final

- [ ] **Step 1: Rodar todos os testes**

```bash
python manage.py test reports -v 2
```

Resultado esperado: todos os testes passam sem erros.

- [ ] **Step 2: Rodar os testes do app registers para garantir sem regressões**

```bash
python manage.py test registers -v 2
```

Resultado esperado: todos passam.

- [ ] **Step 3: Commit de encerramento (se houver alterações não commitadas)**

```bash
git status
# Se houver arquivos modificados não commitados:
git add .
git commit -m "chore: finalize installment expenses modal implementation"
```
