# Installment Monthly Card — AJAX Modal Design

**Date:** 2026-06-15  
**Status:** Approved

## Goal

Transform the `installment_monthly_card.html` summary card into an interactive portal. Clicking an info icon on the card opens a modal that fetches and lists every individual expense linked to an installment plan for the selected month/year, allowing the user to verify which expenses compose the displayed total.

## Approach

AJAX-loaded modal (Option B), consistent with the existing patterns of `expense_details_ajax` and `recurring_expense_details_ajax`. Data is lazy-loaded on modal open, keeping the initial page payload unchanged.

## Components

### 1. `installment_monthly_card.html` (modified)

- Add `data-month` and `data-year` attributes to the card root element, populated from the Django template context variables `installment_monthly_summary` or filter_form context.
- Add a `<button>` with `fa-info-circle` icon beside the "Monthly Installments:" label — same pattern as `monthly_budget_card.html`.
- Embed the modal markup (`installmentExpensesModal`) at the end of the file, following the pattern of `budgetBreakdownModal`.
- Add inline `<script>` that:
  1. On button click: shows the modal and calls `loadInstallmentExpenses(month, year)`.
  2. `loadInstallmentExpenses(month, year)`: fetches `/installment-expenses-ajax/?month=M&year=Y` with `X-Requested-With: XMLHttpRequest` header.
  3. On success: renders expense rows into the modal list container.
  4. On error: displays an error message inside the list container.
  5. Closes modal on overlay click or `fa-times` button.

**Month/year source:** Read from `data-month` / `data-year` on the card element, set via Django template tags. This avoids global JS variables.

### 2. Modal structure

Follows `budgetBreakdownModal` styling:
- Overlay: `fixed inset-0 bg-black/60 flex items-center justify-center z-50`
- Container: `bg-zinc-800 rounded-xl shadow-xl p-6 w-96 max-w-[90vw] max-h-[80vh] flex flex-col`
- Header: title (translated) + `fa-times` close button
- Body: scrollable list, initially shows a spinner (`fa-spinner fa-spin`)
- Each expense row:
  - Description (white, truncated)
  - Date (gray, small)
  - Category badge: `bg-zinc-600 text-gray-300`
  - Payment method badge: `bg-blue-900/50 text-blue-300`
  - Amount: `text-purple-400 font-semibold`
- Footer: divider + total label + total amount in `text-purple-400 font-bold`

### 3. New AJAX endpoint — `installment_expenses_ajax`

**File:** `reports/views.py`

**URL:** `GET /installment-expenses-ajax/`

**Headers required:** `X-Requested-With: XMLHttpRequest`

**Query params:**
- `month` (int, 1–12)
- `year` (int, e.g. 2026)

**Response (200):**
```json
{
  "month": 6,
  "year": 2026,
  "expenses": [
    {
      "description": "iPhone 15 3/12",
      "amount": 500.0,
      "date": "2026-06-15",
      "category": "Eletrônicos",
      "payment_method": "Nubank",
      "installment_plan": "iPhone 15"
    }
  ],
  "total_amount": 1500.0,
  "count": 3
}
```

**Error responses:** 400 for missing/invalid params, 500 for server errors — consistent with existing AJAX views.

**Auth:** `@login_required` decorator.

### 4. New repository method — `get_monthly_installment_expenses_detail`

**File:** `reports/repository/installment_repository.py`

```python
def get_monthly_installment_expenses_detail(
    self, month: int, year: int, user=None
) -> QuerySet:
```

- Filters `Expense` where `installment_plan__isnull=False`, `date__month=month`, `date__year=year`.
- Applies `user` filter if provided.
- Uses `.select_related('category', 'payment_method', 'installment_plan')` to avoid N+1.
- Returns `.values('id', 'description', 'amount', 'date', 'category__name', 'payment_method__name', 'installment_plan__description')` ordered by `-amount`.

### 5. URL registration

**File:** `finance/urls.py` (or `reports/urls.py` if a separate router exists)

```python
path('installment-expenses-ajax/', views.installment_expenses_ajax, name='installment_expenses_ajax'),
```

### 6. Internationalization

New strings to add to `locale/en/LC_MESSAGES/django.po` and `locale/pt_BR/LC_MESSAGES/django.po`:

- `"Installment Expenses"` / `"Despesas de Parcelas"`
- `"No installment expenses found for this period."` / `"Nenhuma despesa de parcela encontrada para este período."`
- `"Installment Plan"` / `"Plano de Parcelas"`

Run `python manage.py compilemessages` after updating `.po` files.

## Data Flow

```
User clicks info icon on installment_monthly_card
  → JS reads data-month / data-year from card element
  → Modal opens, spinner shown
  → fetch('/installment-expenses-ajax/?month=M&year=Y', {headers: {'X-Requested-With': 'XMLHttpRequest'}})
    → installment_expenses_ajax view
      → InstallmentRepository.get_monthly_installment_expenses_detail(month, year, user)
        → Expense.objects filtered by installment_plan__isnull=False + month + year
      → JsonResponse with expenses list + total
  → JS renders rows into modal body
  → User sees list; closes modal via overlay click or × button
```

## Files Modified / Created

| File | Change |
|---|---|
| `reports/templates/reports/components/installment_monthly_card.html` | Add info button, modal markup, JS fetch logic |
| `reports/views.py` | Add `installment_expenses_ajax` view function |
| `reports/repository/installment_repository.py` | Add `get_monthly_installment_expenses_detail` method |
| `finance/urls.py` | Register new URL pattern |
| `locale/en/LC_MESSAGES/django.po` | New translation strings |
| `locale/pt_BR/LC_MESSAGES/django.po` | New translation strings |

## Constraints

- No new JS files — inline `<script>` only, consistent with other cards.
- No new CSS — Tailwind utility classes only.
- Follows `@login_required` + `X-Requested-With` validation pattern of all existing AJAX views.
- The modal does **not** cache results between opens — each open triggers a fresh fetch to reflect any newly added expenses.
