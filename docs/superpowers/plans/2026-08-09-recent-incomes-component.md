# Recent Incomes Component Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Recent Incomes" list to the income registration page (mirroring "Recent Expenses"), keep the user on the income form after a successful submit (showing a success message instead of redirecting away), and make sure every new/changed string is translated in `pt_BR` and `en`.

**Architecture:** Mirrors the existing expense pattern — `RecentIncomeRepository` (data access) → `RecentIncomeService` (formatting) → 3 AJAX views (`recent_incomes_ajax`, `income_autofill_ajax`, `delete_income`) → a template component + a plain-JS module (`recent_incomes.js`) that fetches and renders it. Trimmed relative to expense: no details modal, no autofill of payment method/installments (income doesn't have those fields).

**Tech Stack:** Django 5.1 views/templates, vanilla JS (`fetch`), Django `gettext`/`.po` files. No new dependencies.

## Global Constraints

- Reuse `ExpenseConstants.RECENT_EXPENSES_LIMIT` (10) for the incomes list limit — do not add a new constant for the same value.
- Follow the existing service/repository layering (see `RecentExpenseService`/`RecentExpenseRepository`) — don't put query logic directly in views.
- All user-facing strings must go through `{% trans %}` (templates), `gettext`/`_()` (Python), or a `window.RecentIncomesI18n` object (JS) — mirroring `window.RecentExpensesI18n`.
- Every new `msgid` needs a real (non-empty, non-fuzzy) `msgstr` in both `locale/pt_BR/LC_MESSAGES/django.po` and `locale/en/LC_MESSAGES/django.po`.
- Out of scope: details modal, "edit" link, per-field error messages on the income form.

---

### Task 1: Repository + Service for recent incomes

**Files:**
- Create: `registers/repository/recent_income_repository.py`
- Modify: `registers/repository/__init__.py`
- Create: `registers/services/recent_income_service.py`
- Modify: `registers/services/__init__.py`
- Test: `registers/tests/test_recent_income.py`

**Interfaces:**
- Produces: `RecentIncomeRepository.get_recent_incomes_for_user(user, limit=10) -> QuerySet[Income]`, `RecentIncomeRepository.get_income_by_id_for_user(income_id, user) -> Income | None`.
- Produces: `RecentIncomeService.get_recent_incomes(user) -> list[dict]` with keys `id, description, amount, amount_formatted, date, date_formatted, category_name, category_id`. `RecentIncomeService.get_income_for_autofill(income_id, user) -> dict | None` with keys `description, amount, date, category_id`.

- [ ] **Step 1: Write the failing tests**

Create `registers/tests/test_recent_income.py`:

```python
"""
Tests for the recent-incomes repository and service.
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, Income
from registers.repository.recent_income_repository import RecentIncomeRepository
from registers.services.recent_income_service import RecentIncomeService


class RecentIncomeRepositoryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.other_user = User.objects.create_user(username='otheruser', password='12345')
        self.category = Category.objects.create(name='Salary', type='income')
        self.repository = RecentIncomeRepository()

    def test_get_recent_incomes_for_user_excludes_other_users(self):
        Income.objects.create(
            user=self.user, description='Paycheck', amount=1000,
            date=date(2026, 7, 1), category=self.category,
        )
        Income.objects.create(
            user=self.other_user, description='Other income', amount=500,
            date=date(2026, 7, 1), category=self.category,
        )

        incomes = list(self.repository.get_recent_incomes_for_user(self.user))

        self.assertEqual(len(incomes), 1)
        self.assertEqual(incomes[0].description, 'Paycheck')

    def test_get_recent_incomes_for_user_respects_limit(self):
        for i in range(3):
            Income.objects.create(
                user=self.user, description=f'Income {i}', amount=100,
                date=date(2026, 7, 1), category=self.category,
            )

        incomes = list(self.repository.get_recent_incomes_for_user(self.user, limit=2))

        self.assertEqual(len(incomes), 2)

    def test_get_income_by_id_for_user_returns_none_for_other_users_income(self):
        income = Income.objects.create(
            user=self.other_user, description='Other income', amount=500,
            date=date(2026, 7, 1), category=self.category,
        )

        result = self.repository.get_income_by_id_for_user(income.id, self.user)

        self.assertIsNone(result)

    def test_get_income_by_id_for_user_returns_matching_income(self):
        income = Income.objects.create(
            user=self.user, description='Paycheck', amount=1000,
            date=date(2026, 7, 1), category=self.category,
        )

        result = self.repository.get_income_by_id_for_user(income.id, self.user)

        self.assertEqual(result, income)


class RecentIncomeServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Salary', type='income')
        self.service = RecentIncomeService()

    def test_get_recent_incomes_formats_currency_and_date(self):
        Income.objects.create(
            user=self.user, description='Paycheck', amount='1234.50',
            date=date(2026, 7, 1), category=self.category,
        )

        incomes = self.service.get_recent_incomes(self.user)

        self.assertEqual(len(incomes), 1)
        income = incomes[0]
        self.assertEqual(income['description'], 'Paycheck')
        self.assertEqual(income['amount_formatted'], 'R$ 1.234,50')
        self.assertEqual(income['date_formatted'], '01/07/2026')
        self.assertEqual(income['category_name'], 'Salary')

    def test_get_income_for_autofill_returns_none_when_not_found(self):
        result = self.service.get_income_for_autofill(999999, self.user)

        self.assertIsNone(result)

    def test_get_income_for_autofill_returns_form_fields(self):
        income = Income.objects.create(
            user=self.user, description='Paycheck', amount='1234.50',
            date=date(2026, 7, 1), category=self.category,
        )

        result = self.service.get_income_for_autofill(income.id, self.user)

        self.assertEqual(result['description'], 'Paycheck')
        self.assertEqual(result['amount'], '1234.500')
        self.assertEqual(result['date'], '2026-07-01')
        self.assertEqual(result['category_id'], self.category.id)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test registers.tests.test_recent_income -v 2`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'registers.repository.recent_income_repository'`.

- [ ] **Step 3: Create the repository**

Create `registers/repository/recent_income_repository.py`:

```python
"""
Repository para acesso a dados de entradas (incomes) recentes.

Segue o Repository Pattern com queries otimizadas usando select_related.
"""

from typing import Optional
from django.db.models import QuerySet
from django.contrib.auth.models import User

from registers.models import Income
from registers.constants import ExpenseConstants


class RecentIncomeRepository:
    """Repository para acesso a dados de incomes recentes."""

    def get_recent_incomes_for_user(
        self,
        user: User,
        limit: int = ExpenseConstants.RECENT_EXPENSES_LIMIT
    ) -> QuerySet:
        """
        Retorna as incomes mais recentes do usuário.

        Args:
            user: Usuário logado
            limit: Número máximo de registros (default: 10)

        Returns:
            QuerySet otimizado com select_related
        """
        return (
            Income.objects
            .filter(user=user)
            .select_related('category')
            .order_by('-updated_at')[:limit]
        )

    def get_income_by_id_for_user(
        self,
        income_id: int,
        user: User
    ) -> Optional[Income]:
        """
        Retorna uma income específica com verificação de propriedade.

        Args:
            income_id: ID da income
            user: Usuário logado

        Returns:
            Income se encontrada e pertence ao usuário, None caso contrário
        """
        try:
            return (
                Income.objects
                .select_related('category')
                .get(id=income_id, user=user)
            )
        except Income.DoesNotExist:
            return None
```

Update `registers/repository/__init__.py`:

```python
"""
Repository module for registers application.

Provides data access layer following the Repository Pattern.
"""

from .recent_expense_repository import RecentExpenseRepository
from .recent_income_repository import RecentIncomeRepository

__all__ = ['RecentExpenseRepository', 'RecentIncomeRepository']
```

- [ ] **Step 4: Create the service**

Create `registers/services/recent_income_service.py`:

```python
"""
Service para lógica de negócio de entradas (incomes) recentes.
"""

from typing import List, Dict, Any, Optional
from django.contrib.auth.models import User

from registers.repository.recent_income_repository import RecentIncomeRepository


class RecentIncomeService:
    """Service para operações de incomes recentes."""

    def __init__(self, repository: Optional[RecentIncomeRepository] = None):
        self.repository = repository or RecentIncomeRepository()

    def get_recent_incomes(self, user: User) -> List[Dict[str, Any]]:
        """Retorna incomes recentes formatadas para exibição."""
        incomes = self.repository.get_recent_incomes_for_user(user)

        return [
            self._format_income_for_list(income)
            for income in incomes
        ]

    def get_income_for_autofill(
        self,
        income_id: int,
        user: User
    ) -> Optional[Dict[str, Any]]:
        """Retorna dados de uma income formatados para autofill do formulário."""
        income = self.repository.get_income_by_id_for_user(income_id, user)

        if income is None:
            return None

        return self._format_income_for_autofill(income)

    def _format_income_for_list(self, income) -> Dict[str, Any]:
        """Formata income para exibição na lista."""
        return {
            'id': income.id,
            'description': income.description,
            'amount': float(income.amount),
            'amount_formatted': self._format_currency(income.amount),
            'date': income.date.isoformat(),
            'date_formatted': income.date.strftime('%d/%m/%Y'),
            'category_name': income.category.name if income.category else None,
            'category_id': income.category.id if income.category else None,
        }

    def _format_income_for_autofill(self, income) -> Dict[str, Any]:
        """Formata income para preencher o formulário."""
        return {
            'description': income.description,
            'amount': str(income.amount),
            'date': income.date.isoformat(),
            'category_id': income.category.id if income.category else '',
        }

    def _format_currency(self, value) -> str:
        """Formata valor como moeda brasileira (R$ X.XXX,XX)."""
        if value is None:
            return 'R$ 0,00'

        formatted = "R$ {:,.2f}".format(float(value))
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
```

Update `registers/services/__init__.py`:

```python
"""
Services module for registers app.

This module provides organized service classes for different business logic operations.
"""

from .expense_service import ExpenseService
from .installment_service import InstallmentService
from .income_service import IncomeService
from .csv_import_service import CSVImportService
from .recent_expense_service import RecentExpenseService
from .recent_income_service import RecentIncomeService
from .quick_fill_preset_service import QuickFillPresetService

__all__ = [
    'ExpenseService',
    'InstallmentService',
    'IncomeService',
    'CSVImportService',
    'RecentExpenseService',
    'RecentIncomeService',
    'QuickFillPresetService',
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test registers.tests.test_recent_income -v 2`
Expected: PASS (7 tests).

- [ ] **Step 6: Commit**

```bash
git add registers/repository/recent_income_repository.py registers/repository/__init__.py \
        registers/services/recent_income_service.py registers/services/__init__.py \
        registers/tests/test_recent_income.py
git commit -m "feat: add repository and service for recent incomes"
```

---

### Task 2: Backend views, URLs, and the no-redirect success flow

**Files:**
- Modify: `registers/constants.py`
- Modify: `registers/views.py`
- Modify: `registers/urls.py`
- Test: `registers/tests/test_recent_income.py` (append)

**Interfaces:**
- Consumes: `RecentIncomeService` from Task 1 (`get_recent_incomes`, `get_income_for_autofill`).
- Produces: URL names `recent_incomes_ajax` (GET), `income_autofill_ajax` (GET, `pk`), `delete_income` (POST, `pk`). `register_income` now redirects to `register_income` (not `expense_success`) and sets a `messages.success` on success.

- [ ] **Step 1: Write the failing tests**

Append to `registers/tests/test_recent_income.py`:

```python
from django.contrib import messages as django_messages
from django.urls import reverse


class RegisterIncomeSuccessFlowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='Salary', type='income')

    def test_successful_post_redirects_to_register_income(self):
        response = self.client.post(reverse('register_income'), {
            'description': 'Paycheck',
            'amount': '1000',
            'date': '2026-07-01',
            'category': self.category.id,
        })

        self.assertRedirects(response, reverse('register_income'))
        self.assertEqual(Income.objects.count(), 1)

    def test_successful_post_sets_success_message(self):
        response = self.client.post(reverse('register_income'), {
            'description': 'Paycheck',
            'amount': '1000',
            'date': '2026-07-01',
            'category': self.category.id,
        }, follow=True)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].level, django_messages.SUCCESS)
        self.assertIn('Paycheck', str(messages[0]))


class RecentIncomesAjaxViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.other_user = User.objects.create_user(username='otheruser', password='12345')
        self.category = Category.objects.create(name='Salary', type='income')
        self.client.force_login(self.user)

    def test_recent_incomes_ajax_returns_only_own_incomes(self):
        Income.objects.create(
            user=self.user, description='Paycheck', amount=1000,
            date=date(2026, 7, 1), category=self.category,
        )
        Income.objects.create(
            user=self.other_user, description='Other', amount=500,
            date=date(2026, 7, 1), category=self.category,
        )

        response = self.client.get(reverse('recent_incomes_ajax'))
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['incomes'][0]['description'], 'Paycheck')

    def test_income_autofill_ajax_returns_form_data(self):
        income = Income.objects.create(
            user=self.user, description='Paycheck', amount=1000,
            date=date(2026, 7, 1), category=self.category,
        )

        response = self.client.get(reverse('income_autofill_ajax', args=[income.id]))
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['form_data']['description'], 'Paycheck')

    def test_income_autofill_ajax_404_for_other_users_income(self):
        income = Income.objects.create(
            user=self.other_user, description='Other', amount=500,
            date=date(2026, 7, 1), category=self.category,
        )

        response = self.client.get(reverse('income_autofill_ajax', args=[income.id]))

        self.assertEqual(response.status_code, 404)

    def test_delete_income_removes_own_income(self):
        income = Income.objects.create(
            user=self.user, description='Paycheck', amount=1000,
            date=date(2026, 7, 1), category=self.category,
        )

        response = self.client.post(reverse('delete_income', args=[income.id]))
        data = response.json()

        self.assertTrue(data['success'])
        self.assertFalse(Income.objects.filter(id=income.id).exists())

    def test_delete_income_rejects_other_users_income(self):
        income = Income.objects.create(
            user=self.other_user, description='Other', amount=500,
            date=date(2026, 7, 1), category=self.category,
        )

        response = self.client.post(reverse('delete_income', args=[income.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Income.objects.filter(id=income.id).exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test registers.tests.test_recent_income -v 2`
Expected: FAIL — `NoReverseMatch: Reverse for 'recent_incomes_ajax' not found` (and the redirect test fails because it still points at `expense_success`).

- [ ] **Step 3: Add the new API messages**

In `registers/constants.py`, inside `class ApiMessages:`, add below the existing expense ones:

```python
    INCOME_NOT_FOUND = gettext_noop("Income not found")
    INCOME_DELETE_SUCCESS = gettext_noop("Income '%(description)s' deleted successfully")
    INCOME_AUTOFILL_SUCCESS = gettext_noop("Income data retrieved for autofill")
    RECENT_INCOMES_SUCCESS = gettext_noop("Recent incomes retrieved")
```

- [ ] **Step 4: Import `Income` and `RecentIncomeService` in `views.py`**

In `registers/views.py`, change:

```python
from .models import Expense, Category, CategoryBudgetEstimate
```
to:
```python
from .models import Expense, Income, Category, CategoryBudgetEstimate
```

And change:
```python
from .services import (
    ExpenseService,
    InstallmentService,
    IncomeService,
    CSVImportService,
    RecentExpenseService,
    QuickFillPresetService,
)
```
to:
```python
from .services import (
    ExpenseService,
    InstallmentService,
    IncomeService,
    CSVImportService,
    RecentExpenseService,
    RecentIncomeService,
    QuickFillPresetService,
)
```

Add a module-level instance next to `recent_expense_service = RecentExpenseService()`:

```python
recent_income_service = RecentIncomeService()
```

- [ ] **Step 5: Update `register_income` to not redirect away on success**

Replace:

```python
@login_required
def register_income(request):
    if (request.method == 'POST'):
        form = IncomeForm(request.POST)
        if not form.is_valid():
            return render(request, 'register/income_form.html', {'form': form})
        income_data = form.cleaned_data

        user = request.user
        income = income_service.create_income(user, income_data)

        return redirect('expense_success')

    else:
        form = IncomeForm()
    return render(request, 'register/income_form.html', {'form': form})
```

with:

```python
@login_required
def register_income(request):
    if (request.method == 'POST'):
        form = IncomeForm(request.POST)
        if not form.is_valid():
            return render(request, 'register/income_form.html', {'form': form})
        income_data = form.cleaned_data

        user = request.user
        income = income_service.create_income(user, income_data)
        messages.success(
            request,
            _("Income %(income)s has been registered.") % {'income': str(income)}
        )

        return redirect('register_income')

    else:
        form = IncomeForm()
    return render(request, 'register/income_form.html', {'form': form})
```

- [ ] **Step 6: Add the three AJAX views**

Add right after `income_success` (around line 154 in the current file):

```python
@login_required
@require_http_methods(["GET"])
def recent_incomes_ajax(request):
    """AJAX endpoint para listar entradas (incomes) recentes do usuário."""
    try:
        incomes = recent_income_service.get_recent_incomes(request.user)

        return JsonResponse({
            'success': True,
            'message': _(ApiMessages.RECENT_INCOMES_SUCCESS),
            'incomes': incomes,
            'count': len(incomes),
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=ApiStatus.SERVER_ERROR)


@login_required
@require_http_methods(["GET"])
def income_autofill_ajax(request, pk):
    """AJAX endpoint para obter dados de uma income para autofill do formulário."""
    try:
        form_data = recent_income_service.get_income_for_autofill(pk, request.user)

        if form_data is None:
            return JsonResponse({
                'success': False,
                'error': _(ApiMessages.INCOME_NOT_FOUND),
            }, status=ApiStatus.NOT_FOUND)

        return JsonResponse({
            'success': True,
            'message': _(ApiMessages.INCOME_AUTOFILL_SUCCESS),
            'form_data': form_data,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=ApiStatus.SERVER_ERROR)


@login_required
@require_http_methods(["POST"])
def delete_income(request, pk):
    """Delete an individual income via AJAX"""
    try:
        income = Income.objects.get(pk=pk)

        if income.user != request.user:
            return JsonResponse({'error': _('Unauthorized')}, status=403)

        description = income.description
        income.delete()

        return JsonResponse({
            'success': True,
            'message': _(ApiMessages.INCOME_DELETE_SUCCESS) % {
                'description': description
            }
        })
    except Income.DoesNotExist:
        return JsonResponse({'error': _(ApiMessages.INCOME_NOT_FOUND)}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

- [ ] **Step 7: Add the URLs**

In `registers/urls.py`, replace:

```python
    path("income", views.register_income,
         name="register_income"),
```
with:
```python
    path("income", views.register_income,
         name="register_income"),
    path("income/recent/", views.recent_incomes_ajax, name="recent_incomes_ajax"),
    path("income/<int:pk>/autofill/", views.income_autofill_ajax, name="income_autofill_ajax"),
    path("income/<int:pk>/delete/", views.delete_income, name="delete_income"),
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python manage.py test registers.tests.test_recent_income -v 2`
Expected: PASS (13 tests total).

- [ ] **Step 9: Run the full registers test suite to check for regressions**

Run: `python manage.py test registers`
Expected: PASS, no failures (in particular `test_recurring_expense_checkbox.py` should be unaffected).

- [ ] **Step 10: Commit**

```bash
git add registers/constants.py registers/views.py registers/urls.py registers/tests/test_recent_income.py
git commit -m "feat: add recent-incomes AJAX endpoints and stop redirecting away on income success"
```

---

### Task 3: Frontend — template component and JS module

**Files:**
- Create: `registers/templates/register/components/recent_incomes_table.html`
- Create: `registers/static/js/recent_incomes.js`
- Modify: `registers/templates/register/income_form.html`

**Interfaces:**
- Consumes: `recent_incomes_ajax` (`GET /register/income/recent/`), `income_autofill_ajax` (`GET /register/income/{id}/autofill/`), `delete_income` (`POST /register/income/{id}/delete/`) from Task 2. Response shapes: `{success, incomes: [{id, description, amount_formatted, date_formatted, category_name, category_id}], count}`, `{success, form_data: {description, amount, date, category_id}}`, `{success, message}`.
- Consumes: `window.RecentIncomesI18n` object defined inline in `income_form.html` (keys: `use, delete, confirmDelete, loadError, connectionError, deleteError, autofillError`).

- [ ] **Step 1: Create the recent-incomes template component**

Create `registers/templates/register/components/recent_incomes_table.html`:

```html
{% load i18n %}
<!-- Recent Incomes Section -->
<section id="recentIncomesSection" class="mt-8 bg-zinc-800/40 p-1 sm:p-6 rounded-lg shadow-lg overflow-hidden">
    <header class="flex justify-between items-center mb-4">
        <h2 class="text-lg sm:text-xl font-semibold text-gray-300">
            <i class="fas fa-history mr-2"></i>{% trans "Recent Incomes" %}
        </h2>
        <button
            id="refreshRecentIncomes"
            type="button"
            class="text-gray-400 hover:text-white transition-colors p-2"
            title="{% trans 'Refresh list' %}"
        >
            <i class="fas fa-sync-alt"></i>
        </button>
    </header>

    <!-- Loading State -->
    <div id="recentIncomesLoading" class="text-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto"></div>
        <p class="text-gray-400 mt-2">{% trans "Loading incomes..." %}</p>
    </div>

    <!-- Error State -->
    <div id="recentIncomesError" class="hidden bg-red-900/20 border border-red-500 p-4 rounded">
        <i class="fas fa-exclamation-triangle text-red-400 mr-2"></i>
        <span id="recentIncomesErrorMessage" class="text-red-300"></span>
    </div>

    <!-- Card Content -->
    <div id="recentIncomesContent" class="hidden">
        <div id="recentIncomesCardList" class="flex flex-col gap-3">
            <!-- Cards populated via JavaScript -->
        </div>
    </div>

    <!-- Empty State -->
    <div id="recentIncomesEmpty" class="hidden text-center py-8 text-gray-400">
        <i class="fas fa-inbox text-4xl mb-3 opacity-50"></i>
        <p>{% trans "No recent incomes found" %}</p>
    </div>
</section>
```

- [ ] **Step 2: Create the JS module**

Create `registers/static/js/recent_incomes.js`:

```javascript
/**
 * Recent Incomes Module
 *
 * Gerencia as interacoes da lista de entradas recentes:
 * - Carregamento via AJAX
 * - Autofill do formulario
 * - Exclusao com confirmacao
 */

const incomeI18n = window.RecentIncomesI18n || {};

const RecentIncomes = {
    ENDPOINTS: {
        RECENT: '/register/income/recent/',
        AUTOFILL: '/register/income/{id}/autofill/',
        DELETE: '/register/income/{id}/delete/',
    },

    elements: {
        loading: null,
        error: null,
        errorMessage: null,
        content: null,
        cardList: null,
        empty: null,
        refreshBtn: null,
    },

    init: function () {
        this.cacheElements();
        this.bindEvents();
        this.loadRecentIncomes();
    },

    cacheElements: function () {
        this.elements.loading = document.getElementById('recentIncomesLoading');
        this.elements.error = document.getElementById('recentIncomesError');
        this.elements.errorMessage = document.getElementById('recentIncomesErrorMessage');
        this.elements.content = document.getElementById('recentIncomesContent');
        this.elements.cardList = document.getElementById('recentIncomesCardList');
        this.elements.empty = document.getElementById('recentIncomesEmpty');
        this.elements.refreshBtn = document.getElementById('refreshRecentIncomes');
    },

    bindEvents: function () {
        if (this.elements.refreshBtn) {
            this.elements.refreshBtn.addEventListener('click', () => this.loadRecentIncomes());
        }

        if (this.elements.cardList) {
            this.elements.cardList.addEventListener('click', (e) => this.handleCardAction(e));
        }
    },

    loadRecentIncomes: function () {
        this.showLoading();

        fetch(this.ENDPOINTS.RECENT, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    this.renderIncomes(data.incomes);
                } else {
                    this.showError(data.error || incomeI18n.loadError || 'Erro ao carregar entradas');
                }
            })
            .catch((error) => {
                console.error('Error loading recent incomes:', error);
                this.showError(incomeI18n.connectionError || 'Erro de conexao ao carregar entradas');
            });
    },

    renderIncomes: function (incomes) {
        if (!incomes || incomes.length === 0) {
            this.showEmpty();
            return;
        }

        this.elements.cardList.innerHTML = incomes.map((income) => this.renderIncomeCard(income)).join('');

        this.hideLoading();
        this.elements.content.classList.remove('hidden');
        this.elements.empty.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    renderIncomeCard: function (income) {
        const subtitle = income.category_name
            ? `${income.date_formatted} &middot; ${income.category_name}`
            : income.date_formatted;

        return `
            <div class="bg-zinc-700/30 rounded-lg p-4 flex flex-col gap-2">
                <p class="text-white font-semibold text-base">${income.description}</p>
                <p class="text-green-400 font-bold text-xl">${income.amount_formatted}</p>
                <p class="text-gray-400 text-sm">${subtitle}</p>
                <div class="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-zinc-600">
                    <button type="button" class="action-btn flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg text-sm transition-colors" data-id="${income.id}" data-action="autofill">
                        <i class="fas fa-copy"></i>${incomeI18n.use || 'Usar'}
                    </button>
                    <button type="button" class="action-btn flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg text-sm transition-colors" data-id="${income.id}" data-description="${income.description}" data-action="delete">
                        <i class="fas fa-trash"></i>${incomeI18n.delete || 'Excluir'}
                    </button>
                </div>
            </div>
        `;
    },

    handleCardAction: function (e) {
        const btn = e.target.closest('.action-btn');
        if (!btn) return;

        const action = btn.dataset.action;
        const id = btn.dataset.id;

        switch (action) {
            case 'autofill':
                this.autofillForm(id);
                break;
            case 'delete':
                this.deleteIncome(id, btn.dataset.description);
                break;
        }
    },

    autofillForm: function (incomeId) {
        const url = this.ENDPOINTS.AUTOFILL.replace('{id}', incomeId);

        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    this.populateForm(data.form_data);
                    this.scrollToForm();
                } else {
                    alert(data.error || incomeI18n.autofillError || 'Erro ao carregar dados');
                }
            })
            .catch((error) => {
                console.error('Error loading autofill data:', error);
                alert(incomeI18n.connectionError || 'Erro de conexao');
            });
    },

    populateForm: function (formData) {
        const fields = {
            id_description: formData.description,
            id_amount: formData.amount,
            id_date: formData.date,
        };

        for (const [fieldId, value] of Object.entries(fields)) {
            const field = document.getElementById(fieldId);
            if (field && value !== undefined && value !== null && value !== '') {
                field.value = value;
            }
        }

        const categorySelect = document.getElementById('id_category');
        if (categorySelect && formData.category_id) {
            categorySelect.value = formData.category_id;
        }
    },

    scrollToForm: function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    deleteIncome: function (incomeId, description) {
        const msg = `${incomeI18n.confirmDelete || 'Deseja realmente excluir a entrada'} "${description}"?`;
        if (!confirm(msg)) {
            return;
        }

        const url = this.ENDPOINTS.DELETE.replace('{id}', incomeId);

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    this.loadRecentIncomes();
                } else {
                    alert(data.error || incomeI18n.deleteError || 'Erro ao excluir entrada');
                }
            })
            .catch((error) => {
                console.error('Error deleting income:', error);
                alert(incomeI18n.connectionError || 'Erro de conexao');
            });
    },

    showLoading: function () {
        this.elements.loading.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.empty.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    hideLoading: function () {
        this.elements.loading.classList.add('hidden');
    },

    showEmpty: function () {
        this.hideLoading();
        this.elements.empty.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    showError: function (message) {
        this.hideLoading();
        this.elements.errorMessage.textContent = message;
        this.elements.error.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.empty.classList.add('hidden');
    },

    getCookie: function (name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + '=') {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },
};

document.addEventListener('DOMContentLoaded', function () {
    RecentIncomes.init();
});
```

- [ ] **Step 3: Wire it into `income_form.html`**

Replace the full contents of `registers/templates/register/income_form.html` with:

```html
{% extends "core/base.html" %}
{% load custom_filters i18n static %}
{% block content %}
    <div class="container mx-auto mt-10 max-w-lg ">
        <h2 class="text-2xl font-bold mb-6 ">{% trans "Register Income" %}</h2>
        <form method="post" class="bg-zinc-800/50 p-6 rounded-lg shadow-lg">
            {% csrf_token %}
            <div class="mb-4 space-y-2">
                <label for="id_description" class=" text-gray-400">{% trans "Description" %}</label>
                {{ form.description|add_class:"w-full px-3 bg-transparent py-2 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" }}
            </div>
            <div class="mb-4 space-y-2">
                <label for="id_amount" class=" text-gray-400">{% trans "Amount" %}</label>
                {{ form.amount|add_class:"w-full px-3 bg-transparent py-2 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" }}
            </div>
            <div class="mb-4 space-y-2">
                <label for="id_date" class=" text-gray-400">{% trans "Date" %}</label>
                {{ form.date|add_class:"w-full px-3 bg-transparent py-2 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" }}
            </div>
            <div class="mb-4 space-y-2">
                <label for="id_category" class=" text-gray-400">{% trans "Category" %}</label>
                {{ form.category|add_class:"w-full px-3 bg-transparent py-2 appearance-none border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 *:bg-zinc-900" }}
            </div>
            <button type="submit"
                    class="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-700">{% trans "Submit" %}</button>
        </form>

        {% if messages %}
            <ul class="messages mt-4 space-y-2">
                {% for message in messages %}
                    <li class="{{ message.tags }} p-4 rounded-lg bg-zinc-700">{{ message }}</li>
                {% endfor %}
            </ul>
        {% endif %}

        {% include "register/components/recent_incomes_table.html" %}
    </div>

    <script>
        window.RecentIncomesI18n = {
            use: "{% trans 'Use' %}",
            delete: "{% trans 'Delete' %}",
            confirmDelete: "{% trans 'Do you really want to delete the income' %}",
            loadError: "{% trans 'Error loading incomes' %}",
            connectionError: "{% trans 'Connection error' %}",
            deleteError: "{% trans 'Error deleting income' %}",
            autofillError: "{% trans 'Error loading data' %}",
        };
    </script>
    <script src="{% static 'js/recent_incomes.js' %}"></script>
{% endblock content %}
```

- [ ] **Step 4: Manual verification in the browser**

Run: `python manage.py runserver`

Then, logged in:
1. Open `/register/income` — confirm the "Recent Incomes" section loads (empty state if no incomes yet).
2. Submit the form — confirm the page reloads showing a green success message and stays on `/register/income` (does not navigate to `/register/expense/success`).
3. Confirm the new income appears at the top of "Recent Incomes".
4. Click "Usar" on a card — confirm description/amount/date/category populate the form.
5. Click "Excluir", confirm the browser `confirm()` dialog, confirm the entry disappears from the list.

- [ ] **Step 5: Commit**

```bash
git add registers/templates/register/components/recent_incomes_table.html \
        registers/static/js/recent_incomes.js \
        registers/templates/register/income_form.html
git commit -m "feat: add recent-incomes list UI to the income registration page"
```

---

### Task 4: i18n — translate every new string

**Files:**
- Modify: `locale/pt_BR/LC_MESSAGES/django.po`
- Modify: `locale/en/LC_MESSAGES/django.po`
- Modify: `locale/pt_BR/LC_MESSAGES/django.mo`, `locale/en/LC_MESSAGES/django.mo` (generated)

**Interfaces:**
- Consumes: every `{% trans %}` / `_()` / `gettext_noop()` call added in Tasks 1–3.

- [ ] **Step 1: Extract new strings**

Run:
```bash
python manage.py makemessages -l pt_BR -l en --ignore=venv
```

This scans templates/Python for `{% trans %}`/`_()`/`gettext_noop()` and appends new `msgid` entries (with empty `msgstr`) to both `.po` files, and updates `#:` file/line comments for existing ones.

- [ ] **Step 2: Verify which entries are new/empty**

Run:
```bash
grep -B1 '^msgstr ""$' locale/pt_BR/LC_MESSAGES/django.po | grep '^msgid'
grep -B1 '^msgstr ""$' locale/en/LC_MESSAGES/django.po | grep '^msgid'
```

Expect to see at least these new `msgid`s show up with an empty `msgstr` (some may already have been empty before this change — only fill the ones introduced by this feature, listed below):
- `"Recent Incomes"`
- `"Loading incomes..."`
- `"No recent incomes found"`
- `"Do you really want to delete the income"`
- `"Error loading incomes"`
- `"Error deleting income"`
- `"Income %(income)s has been registered."`

- [ ] **Step 3: Fill in `locale/pt_BR/LC_MESSAGES/django.po`**

For each `msgid` below, find its (now auto-inserted) entry in the file and set the `msgstr` exactly as shown:

| msgid | msgstr (pt_BR) |
|---|---|
| `Recent Incomes` | `Entradas Recentes` |
| `Loading incomes...` | `Carregando entradas...` |
| `No recent incomes found` | `Nenhuma entrada recente encontrada` |
| `Do you really want to delete the income` | `Deseja realmente excluir a entrada` |
| `Error loading incomes` | `Erro ao carregar entradas` |
| `Error deleting income` | `Erro ao excluir entrada` |
| `Income %(income)s has been registered.` | `Entrada %(income)s registrada com sucesso.` |

- [ ] **Step 4: Fill in `locale/en/LC_MESSAGES/django.po`**

| msgid | msgstr (en) |
|---|---|
| `Recent Incomes` | `Recent Incomes` |
| `Loading incomes...` | `Loading incomes...` |
| `No recent incomes found` | `No recent incomes found` |
| `Do you really want to delete the income` | `Do you really want to delete the income` |
| `Error loading incomes` | `Error loading incomes` |
| `Error deleting income` | `Error deleting income` |
| `Income %(income)s has been registered.` | `Income %(income)s has been registered.` |

- [ ] **Step 5: Confirm no empty/fuzzy entries were introduced by this feature**

Run:
```bash
grep -A1 '^msgid "Recent Incomes"$' locale/pt_BR/LC_MESSAGES/django.po locale/en/LC_MESSAGES/django.po
grep -A1 '^msgid "Income %(income)s has been registered.\"$' locale/pt_BR/LC_MESSAGES/django.po locale/en/LC_MESSAGES/django.po
```
Expected: every `msgstr` line is non-empty, and none of the touched entries have a `#, fuzzy` comment above them (remove that comment line if `makemessages` added one, since we're providing a real translation).

- [ ] **Step 6: Compile messages**

Run:
```bash
python manage.py compilemessages
```
Expected: `processing file django.po in .../locale/pt_BR/LC_MESSAGES` and same for `en`, no errors.

- [ ] **Step 7: Manual verification**

Run `python manage.py runserver`, open `/register/income` with the browser/OS locale (or `?lang=` if the project supports switching, otherwise check `settings.LANGUAGE_CODE`) set to `pt-br`, confirm the new UI text is in Portuguese; switch to `en` and confirm it's in English.

- [ ] **Step 8: Commit**

```bash
git add locale/pt_BR/LC_MESSAGES/django.po locale/pt_BR/LC_MESSAGES/django.mo \
        locale/en/LC_MESSAGES/django.po locale/en/LC_MESSAGES/django.mo
git commit -m "i18n: translate recent-incomes and income success-flow strings"
```
