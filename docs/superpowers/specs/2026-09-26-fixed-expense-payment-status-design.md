# Fixed Expense Payment Status — Design

## Problem

`RecurringExpense` ("despesa fixa") already generates a monthly `Expense`
record automatically, via `recurrence_payment` (management command) or
`RecurringExpenseService.process_recurring_expenses_for_month` (manual
UI trigger). Neither of these — nor the `Expense` model itself — tracks
whether the bill has actually been paid in the real world. The existence
of the `Expense` row only means "the system recorded this month's
occurrence," not "the user paid it." There is no way to mark a fixed
expense as paid/pending for the current month, and no visual indicator
of how many fixed expenses are still pending.

The only related pattern in the codebase, `InstallmentRepository`'s
paid/unpaid split, is inferred from date comparison — it cannot express
"due but not yet paid" vs "due and paid," which is exactly what's needed
here.

## Goals

- Let the user mark a given month's fixed-expense `Expense` as paid or
  pending.
- Show, per fixed expense, whether the current month's occurrence is
  paid, pending, or not generated yet.
- Show a pending count as a visual indicator, both on the fixed-expenses
  page and as a summary on the main dashboard. Dashboard values must
  respect the authenticated user and the month/year selected in the
  report.
- Keep the existing automatic generation flow (cron command + manual
  service call) unchanged in behavior — only the payment status is new.

## Non-goals

- No changes to how/when `Expense` rows are generated (still automatic,
  still monthly, still deduped by date).
- No payment status for manually-entered (non-recurring) expenses —
  those already mean "I paid this" by virtue of being entered.
- No external notifications (email/push). The reminder is purely a
  visual indicator inside the app.
- No new top-level page — the feature lives on the existing fixed
  expenses page and the existing dashboard card.

## Approaches considered

1. **`is_paid`/`paid_at` fields directly on `Expense`** (chosen). Each
   month already produces a new `Expense` row per recurring expense, so
   a field on that row is inherently "per month" with no extra bookkeeping.
2. **Separate `RecurringExpensePayment(recurring_expense, year, month, paid_at)` table.**
   Decouples status from `Expense` entirely, but duplicates what the
   monthly `Expense` row already represents — new model, new migration,
   new repository, for no behavior the chosen approach lacks.
3. **Infer paid/pending from date comparison** (mirrors `Installment`).
   Zero migration, but cannot express "due already, not yet paid" —
   fails the actual requirement (explicit manual marking).

Approach 1 was chosen: smallest diff, fits the existing generation flow,
and is the only option that supports explicit manual marking.

## Design

### 1. Model — `registers/models.py`

Add two fields to `Expense`:

```python
is_paid = models.BooleanField(default=True)
paid_at = models.DateField(null=True, blank=True)
```

`default=True` at the model level means manually-entered expenses and
all pre-existing rows read as "paid" with no data migration/backfill
needed. The fields are only meaningful when `reccurring_expense` is set;
the UI never surfaces them for expenses without that link.

Migration: a plain `makemigrations`/`migrate` adding the two columns.

### 2. Generation flow — nasce pendente

Both places that create the monthly `Expense` from a `RecurringExpense`
must explicitly set `is_paid=False` on creation (the model default of
`True` is for manual expenses, not these):

- `registers/management/commands/recurrence_payment.py` — the
  `Expense.objects.create(...)` call.
- `reports/services/recurring_expense_service.py` —
  `process_recurring_expenses_for_month`'s creation call.

### 3. Service — marking paid/pending

Add to `RecurringExpenseService` (mirrors the existing
`toggle_generate_debit` pattern):

```python
def toggle_paid(self, expense_id, user):
    # fetch Expense filtered by id, user, and reccurring_expense__isnull=False
    # flip is_paid; set paid_at = timezone.localdate() if now paid else None
    # save and return the updated Expense
```

The ownership and recurring-expense constraints must be applied in the
database query itself, rather than fetching by global ID and validating
afterward. This prevents one user from toggling another user's expense
and keeps the endpoint restricted to the feature's intended records.

### 4. Repository — `reports/repository/recurring_expense_repository.py`

Add `get_month_expenses_with_status(self, user, month, year)`: returns
each active `RecurringExpense` for the user together with that month's
`Expense`, when one exists, and exposes `is_paid`/`paid_at` alongside the
existing recurring-expense fields. This does not require a complex ORM
join: the implementation may fetch the recurring expenses and the
matching monthly expenses separately, then associate them by
`reccurring_expense_id`. The important contract is user/month/year
scoping and a bounded number of queries.

An active recurring expense with no matching monthly `Expense` has the
explicit status `not_generated`. It is not counted as pending and its
status control is disabled, because there is no monthly occurrence to
update. Generating missing occurrences remains the responsibility of
the existing command/manual processing flow.

Change `RecurringExpenseService.get_fixed_expenses_summary()` to accept
`user`, `month`, and `year`. The `expense_report` view must pass
`request.user` and its selected report month/year. The summary returns
`pending_count` and `total_count` for that same scope, built from the new
repository method. `total_count` counts generated monthly occurrences;
`not_generated_count` may also be returned for display, but missing
occurrences must not be silently classified as pending.

### 5. View / URL — `reports/views.py` + `reports/urls.py`

One new endpoint, e.g. `POST /recurring-expense/<expense_id>/toggle-paid/`,
following the existing AJAX toggle pattern used for
`toggle_generate_debit`: calls `RecurringExpenseService.toggle_paid`,
returns JSON, and responds with 404 if the expense doesn't belong to the
requesting user or has no `reccurring_expense` link. Keep the existing
CSRF and authentication conventions used by the reports app.

### 6. Templates

- `reports/templates/reports/recurring_expense_list.html`: each row
  gains a Pago/Pendente badge for the current month, clickable to call
  the new toggle endpoint (same interaction style as the existing
  active/inactive toggle icon). Rows without a generated monthly
  `Expense` show a disabled "Não gerada" state instead of a toggle.
- `reports/templates/reports/components/fixed_expenses_card.html`
  (existing dashboard card, extended — no new card file): adds a small
  "X pendentes este mês" sub-line fed by the extended
  `get_fixed_expenses_summary()`.

Update the source JavaScript at
`registers/static/js/recurring_expense_list.js` with the paid-status
AJAX interaction and UI update. Do not edit `staticfiles/` directly;
that directory is generated by `collectstatic`.

Add translation entries for Pago, Pendente, Não gerada, the pending
summary, and success/error AJAX messages in the project's existing
locale files.

### 7. Error handling

- Toggling an expense that doesn't belong to the requesting user, does
  not exist, or has no `reccurring_expense` link returns 404, without
  revealing whether another user's record exists.
- A non-POST request follows the project's existing method-handling
  convention and never changes state.
- A failed AJAX request leaves the current badge unchanged and shows a
  translated error message.

### 8. Testing

- Repository: `get_month_expenses_with_status` returns correct
  pending/paid split, excludes inactive (`generate_debit=False`)
  recurring expenses correctly per existing conventions, scopes by
  user/month/year, and returns `not_generated` when appropriate without
  introducing N+1 queries.
- Service: `toggle_paid` flips status and `paid_at`; rejects toggling
  another user's expense and an `Expense` without a recurring link.
- Generation: both `recurrence_payment` and
  `process_recurring_expenses_for_month` create rows with
  `is_paid=False`.
- View/endpoint: requires authentication and POST, returns the expected
  JSON, enforces ownership, and does not mutate state on errors.
- Summary: uses only the authenticated user's records and respects the
  report's selected month/year.
- Existing manual expense flow: an expense entered through the regular
  form, including one linked to a newly created recurring definition,
  keeps the model default `is_paid=True`.
- Template/JavaScript: renders Pago, Pendente, and Não gerada states and
  updates the badge only after a successful response.

Tests follow existing placement conventions (`registers/tests/`,
`reports/tests/`), run via `python manage.py test`.

## Summary of files touched

- `registers/models.py` (+ migration)
- `registers/management/commands/recurrence_payment.py`
- `reports/services/recurring_expense_service.py`
- `reports/repository/recurring_expense_repository.py`
- `reports/views.py`
- `reports/urls.py`
- `reports/templates/reports/recurring_expense_list.html`
- `reports/templates/reports/components/fixed_expenses_card.html`
- `registers/static/js/recurring_expense_list.js`
- `locale/pt_BR/LC_MESSAGES/django.po`
- `locale/en/LC_MESSAGES/django.po`
- new/updated tests in `registers/tests/` and `reports/tests/`
