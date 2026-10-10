# Reaproveitar Estimativas do Mês Anterior — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Na página `/register/estimativas/`, listar as estimativas do último mês anterior que tenha estimativas e permitir copiá-las (selecionadas ou todas, com valor editável) para o mês selecionado.

**Architecture:** Repository (só consultas) → Service (regras da cópia, dataclasses de entrada/saída) → Views (HTTP: list GET + copy POST) com um formset do Django validando as linhas. Mesmo padrão de `RecentIncomeRepository`/`RecentIncomeService`. Dependências injetadas pelo construtor com default.

**Tech Stack:** Django 5.1, templates Django + Tailwind (classes já usadas no projeto), `django.test.TestCase`, i18n via `django.po`.

**Spec:** `docs/superpowers/specs/2026-10-09-copy-previous-budget-estimates-design.md`

## Global Constraints

- Rodar testes sempre com SQLite local: prefixo `DATABASE_URL=` (sem ele, o Django tenta criar o banco de teste no Supabase de produção e trava pedindo confirmação).
- Ativar o venv antes de qualquer comando: `source venv/bin/activate`.
- Nunca sobrescrever uma estimativa existente no mês de destino.
- O mês de origem é sempre recalculado no servidor; o cliente só envia `category_id`, `selected`, `amount` (+ `month`/`year` de destino e `action`).
- Valor `>= 0`, `max_digits=10`, `decimal_places=2`.
- Prefixo do formset: `copy`. Valores do botão `action`: `selected` e `all`.
- Toda string visível ao usuário passa por `gettext`/`ngettext`/`{% trans %}`/`{% blocktrans %}`, com tradução em `locale/pt_BR` e `locale/en`, sem `#, fuzzy`.
- Comentários e docstrings em português, como no resto de `registers/`.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **POST forjado com o mesmo `category_id` em duas linhas** → deve criar uma estimativa só (a última linha vence), sem `IntegrityError`/500. Teste: Task 2, `test_copy_estimates_dedupes_repeated_categories`.
2. **`month`/`year` ausentes, não numéricos ou fora de 1–12** no POST de cópia → 400, nada criado, sem 500. Teste: Task 3, `test_copy_rejects_invalid_target_month`.
3. **Management form com `INITIAL_FORMS=0` e linha em branco** (POST forjado/incompleto) → não pode dar `KeyError`; trata como nada selecionado. Teste: Task 3, `test_copy_ignores_blank_extra_rows`.
4. **Estimativa criada no destino entre o GET e o POST** → ignorada e contada como `skipped`, valor existente preservado. Teste: Task 2, `test_copy_estimates_skips_existing_categories` (simula exatamente isso: a estimativa existe no destino no momento do POST).

---

## File Structure

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `registers/repository/budget_estimate_repository.py` | Criar | Consultas de `CategoryBudgetEstimate`. |
| `registers/repository/__init__.py` | Alterar | Exportar `BudgetEstimateRepository`. |
| `registers/services/budget_estimate_copy_service.py` | Criar | `CopyItem`, `CopyCandidates`, `CopyResult`, `BudgetEstimateCopyService`. |
| `registers/services/__init__.py` | Alterar | Exportar `BudgetEstimateCopyService`. |
| `registers/forms.py` | Alterar | `EstimateCopyRowForm`, `EstimateCopyFormSet`. |
| `registers/views.py` | Alterar | View `budget_estimate_copy` (POST); contexto de cópia em `budget_estimate_list`. |
| `registers/urls.py` | Alterar | Rota `estimativas/copiar/`. |
| `registers/templates/register/components/estimate_copy_section.html` | Criar | Partial da seção de cópia. |
| `registers/templates/register/budget_estimate_list.html` | Alterar | Incluir o partial. |
| `registers/tests/test_budget_estimate_copy.py` | Criar | Testes de repository, service e views. |
| `locale/pt_BR/LC_MESSAGES/django.po`, `locale/en/LC_MESSAGES/django.po` | Alterar | Traduções. |

---

### Task 1: BudgetEstimateRepository

**Files:**
- Create: `registers/repository/budget_estimate_repository.py`
- Modify: `registers/repository/__init__.py`
- Test: `registers/tests/test_budget_estimate_copy.py`

**Interfaces:**
- Consumes: `registers.models.CategoryBudgetEstimate` (campos `user`, `category`, `amount`, `month`, `year`; unique `(user, category, month, year)`).
- Produces:
  - `BudgetEstimateRepository().get_for_month(user, month: int, year: int) -> QuerySet[CategoryBudgetEstimate]` (com `select_related('category')`, ordenado por `category__name`)
  - `.find_latest_month_before(user, month: int, year: int) -> Optional[tuple[int, int]]` — `(month, year)`
  - `.get_category_ids_for_month(user, month: int, year: int) -> set[int]`
  - `.bulk_create(estimates: list[CategoryBudgetEstimate]) -> list[CategoryBudgetEstimate]`

- [ ] **Step 1: Write the failing tests**

Criar `registers/tests/test_budget_estimate_copy.py`:

```python
"""
Testes da cópia de estimativas do mês anterior (repository, service e views).
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, CategoryBudgetEstimate
from registers.repository.budget_estimate_repository import BudgetEstimateRepository


def make_estimate(user, category, month, year, amount='100.00'):
    return CategoryBudgetEstimate.objects.create(
        user=user, category=category, month=month, year=year, amount=Decimal(amount),
    )


class BudgetEstimateRepositoryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.other_user = User.objects.create_user(username='otheruser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        self.repository = BudgetEstimateRepository()

    def test_find_latest_month_before_skips_empty_months(self):
        make_estimate(self.user, self.market, 8, 2026)

        self.assertEqual(self.repository.find_latest_month_before(self.user, 10, 2026), (8, 2026))

    def test_find_latest_month_before_crosses_year(self):
        make_estimate(self.user, self.market, 12, 2026)

        self.assertEqual(self.repository.find_latest_month_before(self.user, 1, 2027), (12, 2026))

    def test_find_latest_month_before_ignores_same_and_future_months(self):
        make_estimate(self.user, self.market, 10, 2026)
        make_estimate(self.user, self.market, 11, 2026)

        self.assertIsNone(self.repository.find_latest_month_before(self.user, 10, 2026))

    def test_find_latest_month_before_ignores_other_users(self):
        make_estimate(self.other_user, self.market, 8, 2026)

        self.assertIsNone(self.repository.find_latest_month_before(self.user, 10, 2026))

    def test_get_category_ids_for_month(self):
        make_estimate(self.user, self.market, 10, 2026)
        make_estimate(self.user, self.uber, 9, 2026)
        make_estimate(self.other_user, self.uber, 10, 2026)

        self.assertEqual(
            self.repository.get_category_ids_for_month(self.user, 10, 2026),
            {self.market.id},
        )

    def test_get_for_month_orders_by_category_name(self):
        make_estimate(self.user, self.uber, 8, 2026)
        make_estimate(self.user, self.market, 8, 2026)

        names = [e.category.name for e in self.repository.get_for_month(self.user, 8, 2026)]

        self.assertEqual(names, ['Supermercado', 'Uber'])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy`
Expected: ERROR — `ModuleNotFoundError: No module named 'registers.repository.budget_estimate_repository'`

- [ ] **Step 3: Implement the repository**

Criar `registers/repository/budget_estimate_repository.py`:

```python
"""
Repository para acesso a dados de estimativas de orçamento por categoria.
"""

from typing import List, Optional, Set, Tuple

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from registers.models import CategoryBudgetEstimate


class BudgetEstimateRepository:
    """Consultas de CategoryBudgetEstimate, sempre filtradas por usuário."""

    def get_for_month(self, user: User, month: int, year: int) -> QuerySet:
        """Estimativas do mês, com a categoria carregada, ordenadas pelo nome da categoria."""
        return (
            CategoryBudgetEstimate.objects
            .filter(user=user, month=month, year=year)
            .select_related('category')
            .order_by('category__name')
        )

    def find_latest_month_before(self, user: User, month: int, year: int) -> Optional[Tuple[int, int]]:
        """(month, year) mais recente estritamente anterior ao informado que tenha estimativas."""
        latest = (
            CategoryBudgetEstimate.objects
            .filter(user=user)
            .filter(Q(year__lt=year) | Q(year=year, month__lt=month))
            .order_by('-year', '-month')
            .values('month', 'year')
            .first()
        )
        if latest is None:
            return None
        return latest['month'], latest['year']

    def get_category_ids_for_month(self, user: User, month: int, year: int) -> Set[int]:
        """IDs das categorias que já têm estimativa no mês."""
        return set(
            CategoryBudgetEstimate.objects
            .filter(user=user, month=month, year=year)
            .values_list('category_id', flat=True)
        )

    def bulk_create(self, estimates: List[CategoryBudgetEstimate]) -> List[CategoryBudgetEstimate]:
        """Cria todas de uma vez; o Django executa o bulk_create dentro de uma transação."""
        return CategoryBudgetEstimate.objects.bulk_create(estimates)
```

Em `registers/repository/__init__.py`, substituir o import e o `__all__` por:

```python
from .recent_expense_repository import RecentExpenseRepository
from .recent_income_repository import RecentIncomeRepository
from .budget_estimate_repository import BudgetEstimateRepository

__all__ = ['RecentExpenseRepository', 'RecentIncomeRepository', 'BudgetEstimateRepository']
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy`
Expected: `Ran 6 tests` … `OK`

- [ ] **Step 5: Commit**

```bash
git add registers/repository/budget_estimate_repository.py registers/repository/__init__.py registers/tests/test_budget_estimate_copy.py
git commit -m "feat: add BudgetEstimateRepository for budget estimate queries

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: BudgetEstimateCopyService

**Files:**
- Create: `registers/services/budget_estimate_copy_service.py`
- Modify: `registers/services/__init__.py`
- Test: `registers/tests/test_budget_estimate_copy.py` (acrescentar classe)

**Interfaces:**
- Consumes: `BudgetEstimateRepository` (Task 1) — `get_for_month`, `find_latest_month_before`, `get_category_ids_for_month`, `bulk_create`.
- Produces (em `registers.services.budget_estimate_copy_service`):
  - `CopyItem(category_id: int, amount: Decimal)` — dataclass frozen
  - `CopyCandidates(source_month: int, source_year: int, copyable: list[CategoryBudgetEstimate], already_existing: list[CategoryBudgetEstimate])` — dataclass frozen
  - `CopyResult(created: int, skipped: int)` — dataclass frozen
  - `BudgetEstimateCopyService(repository: Optional[BudgetEstimateRepository] = None)`
    - `.get_copy_candidates(user, month: int, year: int) -> Optional[CopyCandidates]`
    - `.copy_estimates(user, month: int, year: int, items: list[CopyItem]) -> CopyResult`

- [ ] **Step 1: Write the failing tests**

No topo de `registers/tests/test_budget_estimate_copy.py`, acrescentar o import:

```python
from registers.services.budget_estimate_copy_service import (
    BudgetEstimateCopyService,
    CopyItem,
    CopyResult,
)
```

No fim do arquivo, acrescentar:

```python
class BudgetEstimateCopyServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        self.pharmacy = Category.objects.create(name='Farmácia', type='expense')
        self.service = BudgetEstimateCopyService()

    def test_get_copy_candidates_returns_none_without_source(self):
        self.assertIsNone(self.service.get_copy_candidates(self.user, 10, 2026))

    def test_get_copy_candidates_splits_copyable_and_existing(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        candidates = self.service.get_copy_candidates(self.user, 10, 2026)

        self.assertEqual((candidates.source_month, candidates.source_year), (8, 2026))
        self.assertEqual([e.category for e in candidates.copyable], [self.market])
        self.assertEqual([e.category for e in candidates.already_existing], [self.uber])

    def test_copy_estimates_creates_with_given_amounts(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        result = self.service.copy_estimates(
            self.user, 10, 2026, [CopyItem(self.market.id, Decimal('720.50'))],
        )

        self.assertEqual(result, CopyResult(created=1, skipped=0))
        created = CategoryBudgetEstimate.objects.get(user=self.user, category=self.market, month=10, year=2026)
        self.assertEqual(created.amount, Decimal('720.50'))

    def test_copy_estimates_skips_existing_categories(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        # Criada no destino depois que a página foi carregada (entre o GET e o POST).
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        result = self.service.copy_estimates(self.user, 10, 2026, [
            CopyItem(self.market.id, Decimal('698.00')),
            CopyItem(self.uber.id, Decimal('999.00')),
        ])

        self.assertEqual(result, CopyResult(created=1, skipped=1))
        uber = CategoryBudgetEstimate.objects.get(user=self.user, category=self.uber, month=10, year=2026)
        self.assertEqual(uber.amount, Decimal('300.00'))

    def test_copy_estimates_ignores_categories_not_in_source(self):
        make_estimate(self.user, self.market, 8, 2026)

        result = self.service.copy_estimates(
            self.user, 10, 2026, [CopyItem(self.pharmacy.id, Decimal('50.00'))],
        )

        self.assertEqual(result, CopyResult(created=0, skipped=0))
        self.assertFalse(CategoryBudgetEstimate.objects.filter(month=10, year=2026).exists())

    def test_copy_estimates_without_source_creates_nothing(self):
        result = self.service.copy_estimates(
            self.user, 10, 2026, [CopyItem(self.market.id, Decimal('50.00'))],
        )

        self.assertEqual(result, CopyResult(created=0, skipped=0))
        self.assertFalse(CategoryBudgetEstimate.objects.exists())

    def test_copy_estimates_dedupes_repeated_categories(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        result = self.service.copy_estimates(self.user, 10, 2026, [
            CopyItem(self.market.id, Decimal('100.00')),
            CopyItem(self.market.id, Decimal('200.00')),
        ])

        self.assertEqual(result, CopyResult(created=1, skipped=0))
        created = CategoryBudgetEstimate.objects.get(user=self.user, category=self.market, month=10, year=2026)
        self.assertEqual(created.amount, Decimal('200.00'))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy`
Expected: ERROR — `ModuleNotFoundError: No module named 'registers.services.budget_estimate_copy_service'`

- [ ] **Step 3: Implement the service**

Criar `registers/services/budget_estimate_copy_service.py`:

```python
"""
Service com as regras de negócio para copiar estimativas de um mês anterior.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from django.contrib.auth.models import User

from registers.models import CategoryBudgetEstimate
from registers.repository.budget_estimate_repository import BudgetEstimateRepository


@dataclass(frozen=True)
class CopyItem:
    """Uma linha a copiar: categoria e o valor (possivelmente ajustado pelo usuário)."""
    category_id: int
    amount: Decimal


@dataclass(frozen=True)
class CopyCandidates:
    """Estimativas do mês de origem, separadas pelo que ainda pode ser copiado."""
    source_month: int
    source_year: int
    copyable: List[CategoryBudgetEstimate]
    already_existing: List[CategoryBudgetEstimate]


@dataclass(frozen=True)
class CopyResult:
    created: int
    skipped: int


class BudgetEstimateCopyService:
    """Copia estimativas do último mês anterior com estimativas para um mês de destino."""

    def __init__(self, repository: Optional[BudgetEstimateRepository] = None):
        self.repository = repository or BudgetEstimateRepository()

    def get_copy_candidates(self, user: User, month: int, year: int) -> Optional[CopyCandidates]:
        """Retorna as estimativas do mês de origem, ou None se não houver mês de origem."""
        source = self.repository.find_latest_month_before(user, month, year)
        if source is None:
            return None

        source_month, source_year = source
        existing_category_ids = self.repository.get_category_ids_for_month(user, month, year)

        copyable, already_existing = [], []
        for estimate in self.repository.get_for_month(user, source_month, source_year):
            if estimate.category_id in existing_category_ids:
                already_existing.append(estimate)
            else:
                copyable.append(estimate)

        return CopyCandidates(source_month, source_year, copyable, already_existing)

    def copy_estimates(self, user: User, month: int, year: int, items: List[CopyItem]) -> CopyResult:
        """Cria no mês de destino as linhas copiáveis; nunca sobrescreve as existentes.

        A origem é recalculada aqui (não confia no cliente): categorias fora da origem
        são descartadas e as que já existem no destino contam como `skipped`.
        """
        candidates = self.get_copy_candidates(user, month, year)
        if candidates is None:
            return CopyResult(created=0, skipped=0)

        copyable_ids = {estimate.category_id for estimate in candidates.copyable}
        existing_ids = {estimate.category_id for estimate in candidates.already_existing}

        # Deduplica por categoria: se a mesma categoria vier duas vezes, vale a última.
        items_by_category = {item.category_id: item for item in items}

        to_create = [
            CategoryBudgetEstimate(
                user=user, category_id=item.category_id, amount=item.amount, month=month, year=year,
            )
            for item in items_by_category.values()
            if item.category_id in copyable_ids
        ]
        skipped = sum(1 for category_id in items_by_category if category_id in existing_ids)

        self.repository.bulk_create(to_create)
        return CopyResult(created=len(to_create), skipped=skipped)
```

Em `registers/services/__init__.py`, acrescentar o import e o nome no `__all__`:

```python
from .quick_fill_preset_service import QuickFillPresetService
from .budget_estimate_copy_service import BudgetEstimateCopyService

__all__ = [
    'ExpenseService',
    'InstallmentService',
    'IncomeService',
    'CSVImportService',
    'RecentExpenseService',
    'RecentIncomeService',
    'QuickFillPresetService',
    'BudgetEstimateCopyService',
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy`
Expected: `Ran 13 tests` … `OK`

- [ ] **Step 5: Commit**

```bash
git add registers/services/budget_estimate_copy_service.py registers/services/__init__.py registers/tests/test_budget_estimate_copy.py
git commit -m "feat: add BudgetEstimateCopyService to copy estimates from previous month

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Formset, URL e view de cópia (POST)

**Files:**
- Modify: `registers/forms.py` (imports no topo; classes novas no fim do arquivo, depois de `CategoryBudgetEstimateForm`)
- Modify: `registers/views.py` (imports ~linhas 1–25; instância de service ~linha 40; view nova depois de `budget_estimate_delete`, no fim do arquivo)
- Modify: `registers/urls.py:37-39`
- Test: `registers/tests/test_budget_estimate_copy.py` (acrescentar classe)

**Interfaces:**
- Consumes: `BudgetEstimateCopyService`, `CopyItem`, `CopyResult` (Task 2).
- Produces:
  - `registers.forms.EstimateCopyRowForm` — campos `category_id` (hidden int), `selected` (bool, opcional), `amount` (decimal ≥ 0)
  - `registers.forms.EstimateCopyFormSet = formset_factory(EstimateCopyRowForm, extra=0)`
  - URL name `budget_estimate_copy` → `/register/estimativas/copiar/` (POST only)
  - `registers.views.budget_estimate_copy_service` — instância de módulo, usada também na Task 4

- [ ] **Step 1: Write the failing tests**

No topo de `registers/tests/test_budget_estimate_copy.py`, acrescentar os imports:

```python
from django.contrib import messages as django_messages
from django.urls import reverse
```

No fim do arquivo, acrescentar:

```python
class BudgetEstimateCopyViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        self.client.force_login(self.user)
        self.url = reverse('budget_estimate_copy')
        self.target_url = reverse('budget_estimate_list') + '?month=10&year=2026'

    def post_data(self, rows, action='selected', month='10', year='2026'):
        """rows: lista de (categoria, valor, marcada)."""
        data = {
            'month': month,
            'year': year,
            'action': action,
            'copy-TOTAL_FORMS': str(len(rows)),
            'copy-INITIAL_FORMS': str(len(rows)),
        }
        for index, (category, amount, selected) in enumerate(rows):
            data[f'copy-{index}-category_id'] = str(category.id)
            data[f'copy-{index}-amount'] = amount
            if selected:
                data[f'copy-{index}-selected'] = 'on'
        return data

    def target_estimates(self):
        return CategoryBudgetEstimate.objects.filter(user=self.user, month=10, year=2026)

    def test_copy_selected_creates_only_checked_rows(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '720.00', True),
            (self.uber, '354.00', False),
        ]))

        self.assertRedirects(response, self.target_url, fetch_redirect_response=False)
        self.assertEqual([e.category for e in self.target_estimates()], [self.market])
        self.assertEqual(self.target_estimates().get().amount, Decimal('720.00'))

    def test_copy_all_ignores_checkboxes(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '700.00', False),
            (self.uber, '360.00', False),
        ], action='all'))

        self.assertRedirects(response, self.target_url, fetch_redirect_response=False)
        amounts = {e.category_id: e.amount for e in self.target_estimates()}
        self.assertEqual(amounts, {self.market.id: Decimal('700.00'), self.uber.id: Decimal('360.00')})

    def test_copy_shows_success_message_with_counts(self):
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        response = self.client.post(self.url, self.post_data([
            (self.market, '698.00', True),
            (self.uber, '354.00', True),
        ]), follow=True)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].level, django_messages.SUCCESS)

    def test_copy_with_nothing_selected_shows_error(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '698.00', False),
        ]), follow=True)

        self.assertFalse(self.target_estimates().exists())
        messages = list(response.context['messages'])
        self.assertEqual(messages[0].level, django_messages.ERROR)

    def test_copy_rejects_negative_amount(self):
        response = self.client.post(self.url, self.post_data([
            (self.market, '-1', True),
        ]), follow=True)

        self.assertFalse(self.target_estimates().exists())
        messages = list(response.context['messages'])
        self.assertEqual(messages[0].level, django_messages.ERROR)

    def test_copy_ignores_blank_extra_rows(self):
        data = self.post_data([], action='all')
        data['copy-TOTAL_FORMS'] = '1'
        data['copy-INITIAL_FORMS'] = '0'

        response = self.client.post(self.url, data, follow=True)

        self.assertFalse(self.target_estimates().exists())
        messages = list(response.context['messages'])
        self.assertEqual(messages[0].level, django_messages.ERROR)

    def test_copy_rejects_invalid_target_month(self):
        for month, year in [('13', '2026'), ('0', '2026'), ('abc', '2026'), ('10', '')]:
            with self.subTest(month=month, year=year):
                response = self.client.post(self.url, self.post_data(
                    [(self.market, '698.00', True)], month=month, year=year,
                ))

                self.assertEqual(response.status_code, 400)
        self.assertFalse(CategoryBudgetEstimate.objects.exclude(month=8).exists())

    def test_copy_requires_login(self):
        self.client.logout()

        response = self.client.post(self.url, self.post_data([(self.market, '698.00', True)]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        self.assertFalse(self.target_estimates().exists())

    def test_copy_get_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy.BudgetEstimateCopyViewTest`
Expected: ERROR — `NoReverseMatch: Reverse for 'budget_estimate_copy' not found`

- [ ] **Step 3: Add the formset**

Em `registers/forms.py`, logo abaixo de `from django import forms` (linha 1), acrescentar:

```python
from django.forms import formset_factory
```

No fim do arquivo, depois de `CategoryBudgetEstimateForm`, acrescentar:

```python
class EstimateCopyRowForm(forms.Form):
    """Uma linha da cópia de estimativas: categoria, se foi marcada e o valor a usar."""
    category_id = forms.IntegerField(widget=forms.HiddenInput)
    selected = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'w-4 h-4 accent-blue-600'}),
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'bg-zinc-700 border border-zinc-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5',
            'step': '0.01',
            'min': '0',
        }),
    )


EstimateCopyFormSet = formset_factory(EstimateCopyRowForm, extra=0)
```

- [ ] **Step 4: Add the view**

Em `registers/views.py`:

1. Na linha 2, acrescentar `EstimateCopyFormSet` ao import de `.forms`:

```python
from .forms import ExpenseForm, IncomeForm, CSVImportForm, RecurringExpenseForm, CSVProcessorForm, QuickFillPresetForm, CategoryBudgetEstimateForm, EstimateCopyFormSet
```

2. Depois de `from .services.expense_list_service import ExpenseListService`, acrescentar:

```python
from .services.budget_estimate_copy_service import BudgetEstimateCopyService, CopyItem
```

3. Trocar `from django.http import JsonResponse, HttpResponse` por:

```python
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.urls import reverse
```

4. Depois de `recurring_expense_service = RecurringExpenseService()` (~linha 40), acrescentar:

```python
budget_estimate_copy_service = BudgetEstimateCopyService()
```

5. No fim do arquivo, depois de `budget_estimate_delete`, acrescentar:

```python
def _parse_target_month(data):
    """Lê month/year do POST; retorna None se ausentes ou inválidos."""
    try:
        month, year = int(data.get('month', '')), int(data.get('year', ''))
    except ValueError:
        return None
    if not 1 <= month <= 12:
        return None
    return month, year


@login_required
@require_http_methods(["POST"])
def budget_estimate_copy(request):
    target = _parse_target_month(request.POST)
    if target is None:
        return HttpResponseBadRequest()
    month, year = target
    redirect_url = f"{reverse('budget_estimate_list')}?month={month}&year={year}"

    formset = EstimateCopyFormSet(request.POST, prefix='copy')
    if not formset.is_valid():
        messages.error(request, _('Invalid values. Check the amounts and try again.'))
        return redirect(redirect_url)

    # "Copiar todas" ignora os checkboxes, mas respeita os valores editados.
    copy_all = request.POST.get('action') == 'all'
    items = [
        CopyItem(form.cleaned_data['category_id'], form.cleaned_data['amount'])
        for form in formset.forms
        if form.cleaned_data and (copy_all or form.cleaned_data['selected'])
    ]
    if not items:
        messages.error(request, _('No estimates selected.'))
        return redirect(redirect_url)

    result = budget_estimate_copy_service.copy_estimates(request.user, month, year, items)

    message = ngettext(
        '%(count)s estimate copied.', '%(count)s estimates copied.', result.created,
    ) % {'count': result.created}
    if result.skipped:
        message += ' ' + ngettext(
            '%(count)s skipped because it already existed.',
            '%(count)s skipped because they already existed.',
            result.skipped,
        ) % {'count': result.skipped}
    messages.success(request, message)
    return redirect(redirect_url)
```

(`form.cleaned_data` vazio acontece só em linha extra em branco — ver Review Focus 3.)

- [ ] **Step 5: Add the URL**

Em `registers/urls.py`, depois da linha `path("estimativas/<int:pk>/excluir/", ...)`, acrescentar:

```python
    path("estimativas/copiar/", views.budget_estimate_copy, name="budget_estimate_copy"),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy`
Expected: `Ran 22 tests` … `OK`

- [ ] **Step 7: Commit**

```bash
git add registers/forms.py registers/views.py registers/urls.py registers/tests/test_budget_estimate_copy.py
git commit -m "feat: add POST endpoint to copy budget estimates (selected or all)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Seção de cópia na página de estimativas

**Files:**
- Create: `registers/templates/register/components/estimate_copy_section.html`
- Modify: `registers/templates/register/budget_estimate_list.html` (antes do `</div>` final que fecha o container, logo após o `{% endif %}` do bloco "No estimates for …")
- Modify: `registers/views.py` — função `budget_estimate_list`
- Test: `registers/tests/test_budget_estimate_copy.py` (acrescentar classe)

**Interfaces:**
- Consumes: `budget_estimate_copy_service.get_copy_candidates` (Task 2), `EstimateCopyFormSet` e URL `budget_estimate_copy` (Task 3).
- Produces: contexto do template `register/budget_estimate_list.html` com
  - `copy_candidates: Optional[CopyCandidates]`
  - `copy_formset: Optional[EstimateCopyFormSet]` (prefixo `copy`)
  - `copy_rows: list[tuple[EstimateCopyRowForm, CategoryBudgetEstimate]]` — cada form pareado com a estimativa de origem

- [ ] **Step 1: Write the failing tests**

No fim de `registers/tests/test_budget_estimate_copy.py`, acrescentar:

```python
class BudgetEstimateListCopySectionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.market = Category.objects.create(name='Supermercado', type='expense')
        self.uber = Category.objects.create(name='Uber', type='expense')
        self.client.force_login(self.user)
        self.url = reverse('budget_estimate_list') + '?month=10&year=2026'

    def test_list_shows_copy_section_from_latest_month(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        response = self.client.get(self.url)

        candidates = response.context['copy_candidates']
        self.assertEqual((candidates.source_month, candidates.source_year), (8, 2026))
        self.assertContains(response, 'Supermercado')
        self.assertContains(response, reverse('budget_estimate_copy'))
        self.assertContains(response, 'name="action" value="all"')

    def test_list_prefills_copyable_rows_checked_with_source_amount(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')

        response = self.client.get(self.url)

        form, estimate = response.context['copy_rows'][0]
        self.assertEqual(estimate.category, self.market)
        self.assertEqual(form.initial, {'category_id': self.market.id, 'selected': True, 'amount': Decimal('698.00')})

    def test_list_marks_existing_categories_as_read_only(self):
        make_estimate(self.user, self.market, 8, 2026, '698.00')
        make_estimate(self.user, self.uber, 8, 2026, '354.00')
        make_estimate(self.user, self.uber, 10, 2026, '300.00')

        response = self.client.get(self.url)

        self.assertEqual([e.category for _, e in response.context['copy_rows']], [self.market])
        self.assertEqual(
            [e.category for e in response.context['copy_candidates'].already_existing],
            [self.uber],
        )

    def test_list_hides_copy_section_without_source(self):
        response = self.client.get(self.url)

        self.assertIsNone(response.context['copy_candidates'])
        self.assertNotContains(response, reverse('budget_estimate_copy'))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy.BudgetEstimateListCopySectionTest`
Expected: FAIL/ERROR — `KeyError: 'copy_candidates'`

- [ ] **Step 3: Pass the copy context in `budget_estimate_list`**

Em `registers/views.py`, na função `budget_estimate_list`, trocar o bloco final (de `estimates = CategoryBudgetEstimate.objects.filter(` até o `return render(...)`) por:

```python
    estimates = CategoryBudgetEstimate.objects.filter(
        user=request.user, month=selected_month, year=selected_year
    ).select_related('category').order_by('category__name')

    copy_candidates = budget_estimate_copy_service.get_copy_candidates(
        request.user, selected_month, selected_year
    )
    copy_formset, copy_rows = None, []
    if copy_candidates:
        copy_formset = EstimateCopyFormSet(prefix='copy', initial=[
            {'category_id': estimate.category_id, 'selected': True, 'amount': estimate.amount}
            for estimate in copy_candidates.copyable
        ])
        copy_rows = list(zip(copy_formset.forms, copy_candidates.copyable))

    return render(request, 'register/budget_estimate_list.html', {
        'estimates': estimates,
        'form': form,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'copy_candidates': copy_candidates,
        'copy_formset': copy_formset,
        'copy_rows': copy_rows,
    })
```

- [ ] **Step 4: Create the partial**

Criar `registers/templates/register/components/estimate_copy_section.html`:

```django
{% load currency_filters i18n %}
{% if copy_candidates %}
<section class="bg-zinc-700/50 rounded-lg p-4 space-y-3" aria-labelledby="copy-estimates-title">
  <h3 id="copy-estimates-title" class="text-sm font-semibold text-gray-300">
    {% blocktrans with month=copy_candidates.source_month year=copy_candidates.source_year %}Estimates from {{ month }}/{{ year }}{% endblocktrans %}
  </h3>

  {% if copy_rows %}
  <form method="post" action="{% url 'budget_estimate_copy' %}" class="space-y-3">
    {% csrf_token %}
    {{ copy_formset.management_form }}
    <input type="hidden" name="month" value="{{ selected_month }}">
    <input type="hidden" name="year" value="{{ selected_year }}">

    <ul class="divide-y divide-zinc-700/50">
      {% for row_form, estimate in copy_rows %}
      <li class="flex items-center gap-3 py-2">
        {{ row_form.category_id }}
        {{ row_form.selected }}
        <label for="{{ row_form.selected.id_for_label }}" class="flex-1 text-white text-sm font-medium">
          {{ estimate.category.name }}
        </label>
        <label for="{{ row_form.amount.id_for_label }}" class="sr-only">
          {% blocktrans with category=estimate.category.name %}Amount for {{ category }}{% endblocktrans %}
        </label>
        <div class="w-36">{{ row_form.amount }}</div>
      </li>
      {% endfor %}
    </ul>

    <div class="flex flex-wrap gap-2 justify-end">
      <button type="submit" name="action" value="selected"
              class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm">
        {% blocktrans with month=selected_month year=selected_year %}Copy selected to {{ month }}/{{ year }}{% endblocktrans %}
      </button>
      <button type="submit" name="action" value="all"
              class="bg-zinc-600 hover:bg-zinc-500 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm">
        {% trans "Copy all" %}
      </button>
    </div>
  </form>
  {% else %}
  <p class="text-gray-500 text-sm">{% trans "All categories already exist this month." %}</p>
  {% endif %}

  {% if copy_candidates.already_existing %}
  <ul class="divide-y divide-zinc-700/50">
    {% for estimate in copy_candidates.already_existing %}
    <li class="flex items-center gap-3 py-2 text-sm text-gray-500">
      <span class="flex-1">{{ estimate.category.name }}</span>
      <span>{{ estimate.amount|format_brl }}</span>
      <span class="text-xs">{% trans "Already exists this month" %}</span>
    </li>
    {% endfor %}
  </ul>
  {% endif %}
</section>
{% endif %}
```

O primeiro botão do formulário é o "selecionadas", então apertar Enter num campo de valor copia só as marcadas.

- [ ] **Step 5: Include the partial in the page**

Em `registers/templates/register/budget_estimate_list.html`, logo depois do `{% endif %}` que fecha o bloco `{% if estimates %} … {% else %} … No estimates for … {% endif %}` e antes do `</div>` final, acrescentar:

```django

  {% include "register/components/estimate_copy_section.html" %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy`
Expected: `Ran 26 tests` … `OK`

- [ ] **Step 7: Commit**

```bash
git add registers/views.py registers/templates/register/components/estimate_copy_section.html registers/templates/register/budget_estimate_list.html registers/tests/test_budget_estimate_copy.py
git commit -m "feat: show previous month estimates with copy options on estimates page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Traduções (pt_BR e en)

**Files:**
- Modify: `locale/pt_BR/LC_MESSAGES/django.po`, `locale/en/LC_MESSAGES/django.po`
- Regenerate: `locale/pt_BR/LC_MESSAGES/django.mo`, `locale/en/LC_MESSAGES/django.mo`

**Interfaces:**
- Consumes: as strings das Tasks 3 e 4.
- Produces: traduções compiladas.

- [ ] **Step 1: Extract the new strings**

Run: `DATABASE_URL= python manage.py makemessages -l pt_BR -l en --ignore=venv`
Expected: `processing locale pt_BR` / `processing locale en`, sem erros.

- [ ] **Step 2: Fill in the translations**

Em `locale/pt_BR/LC_MESSAGES/django.po`, preencher os `msgstr` destas entradas (remover a linha `#, fuzzy` acima de qualquer uma delas se o `makemessages` tiver adicionado):

```po
msgid "Invalid values. Check the amounts and try again."
msgstr "Valores inválidos. Confira os valores e tente novamente."

msgid "No estimates selected."
msgstr "Nenhuma estimativa selecionada."

msgid "%(count)s estimate copied."
msgid_plural "%(count)s estimates copied."
msgstr[0] "%(count)s estimativa copiada."
msgstr[1] "%(count)s estimativas copiadas."

msgid "%(count)s skipped because it already existed."
msgid_plural "%(count)s skipped because they already existed."
msgstr[0] "%(count)s ignorada porque já existia."
msgstr[1] "%(count)s ignoradas porque já existiam."

msgid "Estimates from %(month)s/%(year)s"
msgstr "Estimativas de %(month)s/%(year)s"

msgid "Amount for %(category)s"
msgstr "Valor para %(category)s"

msgid "Copy selected to %(month)s/%(year)s"
msgstr "Copiar selecionadas para %(month)s/%(year)s"

msgid "Copy all"
msgstr "Copiar todas"

msgid "All categories already exist this month."
msgstr "Todas as categorias já existem neste mês."

msgid "Already exists this month"
msgstr "Já existe neste mês"
```

Em `locale/en/LC_MESSAGES/django.po`, **deixar os `msgstr` vazios** (o Django usa o próprio `msgid` em inglês), que é a convenção do arquivo — ex.: `msgid "Estimate created successfully."` tem `msgstr ""`. Só remover `#, fuzzy` se o `makemessages` tiver adicionado.

- [ ] **Step 3: Verify no empty or fuzzy entries among the new strings**

Run:
```bash
for f in locale/pt_BR/LC_MESSAGES/django.po; do
  echo "== $f"
  grep -n -A4 -E 'msgid "(Invalid values\. Check|No estimates selected|%\(count\)s estimate copied|%\(count\)s skipped because it|Estimates from|Amount for|Copy selected to|Copy all|All categories already exist|Already exists this month)' "$f"
done
grep -n -B1 -E 'msgid "(Copy all|Already exists this month|Estimates from)' locale/*/LC_MESSAGES/django.po | grep fuzzy || echo "no fuzzy"
```
Expected: todo `msgstr` mostrado no pt_BR é não vazio, e a última linha imprime `no fuzzy`.

- [ ] **Step 4: Compile and run the whole registers suite**

Run:
```bash
python manage.py compilemessages --ignore=venv
DATABASE_URL= python manage.py test registers
```
Expected: `compilemessages` sem erros; testes: `OK` (54 já existentes + 26 novos = `Ran 80 tests`).

- [ ] **Step 5: Manual check in the browser**

Run: `python manage.py runserver` e abrir `/register/estimativas/?month=10&year=2026` (com dados de produção, onde há estimativas em agosto). Conferir:
- a seção "Estimativas de 8/2026" aparece abaixo da tabela, com as linhas marcadas e os valores de agosto;
- clicar no nome da categoria marca/desmarca o checkbox;
- "Copiar selecionadas para 10/2026" e "Copiar todas" mostram a mensagem de sucesso e as novas linhas aparecem na tabela de outubro;
- depois de copiar, as categorias copiadas aparecem na lista "Já existe neste mês".

Atenção: com o `.env` padrão isso grava no banco de produção. Para testar sem tocar em produção, rode com `DATABASE_URL= python manage.py runserver` (SQLite local).

- [ ] **Step 6: Commit**

```bash
git add locale/
git commit -m "i18n: translate budget estimate copy UI

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
