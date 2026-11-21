# Refactor decision log (2026-11-20)

Question asked of every piece: should these pieces change together?
Additions chosen: **Comments** and **Tests**.

Baseline: `DATABASE_URL= python manage.py test` → 265 tests OK (162 s).

Each fix is written above the problems it solves.

## Status
F1–F12 applied. Python import graph: `utils` ← `registers.models` ← everything else; `registers` no longer imports `reports`.
Verification: full suite green (179 tests, Playwright UI tests included; 265 before pruning); every page checked in a browser against a seeded scratch database (desktop and mobile).

## Fixes and the problems they solve

### F1. Expense queries own the billing-month rule and the user scope
`Expense.objects` gets a QuerySet with `in_billing_month(year, month)` / `in_billing_year(year)`; every report query starts from `Expense.objects.filter(user=user)`. All Python copies of the billing period go.
- `reports/repository/expense_repository.py:10-43` holds the real rule (SQL annotation), but the same rule is re-implemented in `reports/services/billing_period_calculator.py:12-45`, `reports/services/expense_service.py:147-231` (`get_billing_month`, `calculate_end_date`, `calculate_total_expense_for_payment_method`), `registers/utils.py:43-65` (hard-coded 2024) and a hard-coded Nubank calendar in `billing_period_calculator.py:47-109`. Change the rule in one and the others silently disagree.
- `reports/services/expense_calculator.py` and `reports/services/category_calculator.py` exist only to feed the Python copy; nothing live calls them.
- Report queries scope by user inconsistently: `get_total_by_date`, `calculate_global_balance`, category table, payment-method chart, despesas tab, income chart, `get_distinct_years_in_tuples`, installments tab (`views/dashboard.py:151` passes no user) all read every user's rows; `user=None` optional params in `installment_repository.py`, `recurring_expense_repository.py:11`, `expense_repository.py:241` let callers forget. Production has a `testuser` whose 2 expenses leak into Jan/2025 totals.
- `reports/views/expense_update.py:10` and `reports/views/recurring.py:90` (UpdateViews) do not restrict the queryset to the owner; `recurring_expense_delete/toggle` and `delete_expense/delete_income` fetch by pk and compare users afterwards; `RecurringExpenseService.get_recurring_expense_with_expenses` fetches by pk only.
- `export/views.py:33` reaches into `reports.repository.ExpenseRepository` (reports internals) and then adds `.filter(user=...)` itself.

### F2. One money formatter; services return numbers, templates format
`format_brl` lives once in `utils/money.py`; the template filter wraps it; data structures carry Decimals, not pre-formatted strings.
- Seven copies of the R$ formatter: `reports/views/_common.py:25`, `reports/templatetags/currency_filters.py:8`, `reports/dataclasses.py:68`, `reports/services/installment_progress_calculator.py:122`, `reports/services/recurring_expense_service.py:72`, `registers/services/recent_expense_service.py:155`, `registers/services/recent_income_service.py:62`.
- `formatted_*` keys/properties (`formatted_total`, `formatted_total_remaining`, `formatted_paid_amount`, …) duplicate the number next to it; the template could format it.
- `reports/templates/reports/components/expense_category_table.html:16,23` runs `stringformat:'f'` on an already formatted string (heat-map `data-value` gets garbage) and compares against the literal `'R$ 0,00'` (special case tied to the formatter's output).

### F3. Months are numbers; names and parsing come from one place
Use Django's translated `django.utils.dates.MONTHS` for names and one `parse_month_year()` (1–12, 2000–2100) for request input.
- English `calendar.month_name` strings are used as dict keys across services (`expense_service.py:358`, `utils/dates.py:9-20`) and translated back in the template (`currency_filters.translate_month`); `reports/views/expense_list.py:17` keeps its own `MONTHS_PT`.
- Month/year validation is copied in `reports/views/expense_list.py:25-29`, `reports/views/recurring.py:46-54,246-251`, `reports/services/recurring_payment_service.py:17`, `reports/services/recurring_expense_service.py:236-253`, `registers/views.py:991-999` (`_parse_target_month`); `reports/views/_common.py:16`, `registers/views.py:916` and `export/views.py:20` don't validate at all (bad `?month=` → 500).
- `ExpenseRepository.get_months_by_year`, `get_months_in_list`, `get_distinct_months_in_tuples`, `get_months_in_database` are four more month-list helpers, all dead.

### F4. A recurring expense knows its own monthly occurrence
`RecurringExpense.due_date(year, month)` (clamped to the month's last day) and `generate_for_month(year, month)`; "one occurrence per calendar month" is the only existence check. One month overview feeds every consumer.
- Generation is written three times with three different rules: `reports/services/recurring_expense_service.py:220-315` (day 31 in a 30-day month → error), `registers/management/commands/recurrence_payment.py:42-87` (skips with warning, all users, current year only), `recurring_expense_service.py:143-158` sync (clamps). Existence check is by exact date in two places and by month in the third, so an edited date creates a duplicate.
- Month status is computed twice: `recurring_expense_repository.get_month_expenses_with_status` (paid/pending/not_generated) for the fixed-expenses card and the list page, and `recurring_payment_service.get_overview` (overdue/today/upcoming/missing) for the bell and the payments page. They disagree on what "not generated" means.
- `RecurringExpenseService.create_recurring_expense` (`:90`) copies the form's field list by hand and drops `is_international` → creating an international recurring expense loses IOF. `update_recurring_expense` is a dead second copy.
- `registers/views.py:83-95` builds a recurring expense dict by hand inside the expense view (and `registers` imports `reports.services`, the wrong direction).
- Two endpoints change paid state: `recurring_expense_toggle_paid` (unused by the UI) and `recurring_expense_set_paid`; repository has `toggle_paid` and `set_paid`.
- `RecurringExpenseService` methods `toggle_generate_debit`, `delete_recurring_expense`, `set_paid`, `toggle_paid` only forward to the repository; `get_active_fixed_expenses_list`, `get_user_fixed_expenses`, `get_total_inactive_recurring_expenses`, `get_total_all_recurring_expenses`, `get_active_recurring_expenses`, `get_recurring_expenses_by_user` are dead.

### F5. Reports logic: one module per feature, no pass-through layers
`reports/services/` keeps one module per dashboard feature (budget, installments, recurring, yearly charts, daily spending); `reports/repository/`, `reports/dataclasses.py`, `reports/utils.py`, `reports/views/_common.py` singletons go.
- Repository and service layers change together for every card (repository method ↔ service method 1:1): `installment_repository` ↔ `installment_progress_calculator`, `recurring_payment_repository` ↔ `recurring_payment_service`, `budget_estimate_repository` ↔ `budget_estimate_service`, `income_repository` ↔ `expense_service`.
- `reports/views/dashboard.py:52-63` mutates `BudgetSummary` after the service built it (`total_regular`, `adjusted_expected`): the view knows the summary's internals.
- `InstallmentProgressCalculator._create_progress_dataclass` re-copies a dict the repository just built into a dataclass.
- `reports/views/dashboard.py:169-207` and `reports/views/ajax.py:36-50` format the daily trend for Chart.js twice; `DailyExpenseCalculator(year, month)` args are ignored by the trend.
- `ExpenseService.__init__(year=2024)` builds three helper objects only dead methods use.
- Dead: `ExpenseService` methods `calculate_monthly_payment_method_total_expense_datasets`, `calculate_monthly_expenses_total`, `calculate_total_incomes_by_month`, `create_month_total_datasets`, `get_total_expenses_amount_by_payment_method`, `monthly_payment_method_expense_totals`, `get_monthly_category_payment_method_total_expenses` (writes a JSON file to cwd), `get_expenses_by_category_and_payment_method`, `_debug_*`; `debug_to_json` (returns None on line 1), `convert_values_to_float`; `CategoryRepository`, `PaymentMethodRepository` (missing `self`), `IncomeRepository.get_incomes_by_month`; `ExpenseRepository` methods `get_monthly_expenses_by_year`, `get_expenses_by_filter`, `get_expenses_for_year`, `get_expenses_group_by_category_and_month`, `get_monthly_category_payment_method_total_expenses`, `get_expenses_by_category_in_period`, `get_daily_expenses_by_category_in_period`, `get_daily_expenses_by_payment_method_in_period`; `InstallmentRepository.get_open_installment_count`; `InstallmentProgress.is_fully_paid`; `DailyExpenseCalculator.calculate_daily_expenses_for_month`; `reports/management/commands/run_expense_service.py`; `reports/management/commands/measure_performance.py` (calls a `login_required` view without a user — crashes).

### F6. Registers: forms own their fields, views split by feature, no wrappers
- `registers/components/expense_form/*` (ABC with one implementation, `QuickFillMenu`, `QuickFillOption`) builds `ExpenseForm`'s fields from outside the form; `description` there is `max_length=200` while the model column is 100.
- `registers/components/csv_import/csv_import_component.py` is an older copy of `CSVImportService` and cannot even import (`from ..models`).
- `ExpenseService.create_single_expense`, `IncomeService.create_income`, `QuickFillPresetService` (`get_active_presets_for_user` dead; others wrap one ORM call) only forward to the ORM.
- `RecentExpenseService`/`RecentExpenseRepository` and `RecentIncomeService`/`RecentIncomeRepository`: two layers to serialize ten rows; both services carry a formatter copy.
- `registers/constants.py`: `ApiStatus` renames HTTP codes (and views mix it with literals), `ApiMessages` holds strings used once, `ExpenseConstants` copies model field sizes (`MAX_DESCRIPTION_LENGTH`, `MAX_AMOUNT_DIGITS`, `AMOUNT_DECIMAL_PLACES`, unused) and `RECENT_EXPENSES_LIMIT` is also used for incomes.
- `registers/views.py` (1044 lines) mixes eight features; the "flash every form error" loop is copied 6× (`:54,315,441,586,752,804`); the CSV import result messages are copied 2× (`:296-311,357-372`).
- `CSVImportForm` and `CSVProcessorForm` (`registers/forms.py:87-360`) copy `csv_file`, `csv_text`, `separator`, `clean_csv_file`, `clean_csv_text` and the file-or-text check; `clean_csv_text` only accepts `, ; \t` though `|` is offered as a separator.
- Tailwind class strings for inputs/checkboxes/selects are pasted ~15× in `forms.py`.
- `Category.objects.filter(type='expense').order_by('name')` / `PaymentMethod.objects.order_by('name')` repeated in 4 forms and 3 views; `user` kwarg popped and ignored by `RecurringExpenseForm`, `QuickFillPresetForm`.
- `CSVImportService.parse_csv_file` / `parse_csv_file_from_string` and `CSVProcessorService.parse_csv_file` / `parse_csv_from_string` differ only in the source; `import_csv` command re-implements parsing and calls the private `_clean_dataframe`.
- Strategy pattern (`csv_record_strategies.py`, 405 lines): three strategies + factory + `add_strategy` (never called) for "expense or income, by type column or sign"; the create code is copied 4×, defaults `'Outros'`/`'Crédito - Nubank'` copied 5×.
- `CSVImportService` keeps per-import state on a module-level singleton shared by all requests; `_log_warning` is never called so `warnings` is always empty; `get_import_summary` dead; `preview_data` returns the same rows twice.
- Budget estimates: `registers/views.py:935` re-writes `BudgetEstimateRepository.get_for_month`; `budget_estimate_update/delete` hard-code `/register/estimativas/` while `budget_estimate_copy` uses `reverse`; `.get(pk=…)` raises 500 for a missing id.
- Dead: `ExpenseCreateView`, `expense_success` + template + URL, `income_success`, `csv_import_ajax` (stub, `csrf_exempt`), `registers/utils.py`, `import_data` command (legacy one-off importer duplicating CSV import), `QuickFillMenu.get_all_options`.

### F7. Special cases removed by the above
- `print('[DEBUG] …')` in `registers/views.py:47-117`; `print` + traceback in `reports/views/dashboard.py:196`, `ajax.py:53`, `daily_expense_calculator.py`, `recurrence_payment.py`.
- Swallowed exceptions returning `str(e)` as JSON 500 in 10 registers/reports AJAX views; `get_daily_spending_data` returns empty data on any error; `DailyExpenseCalculator` swallows query errors.
- `'Investimento'` payment method excluded from totals by name (`reports/services/expense_service.py:454`).
- `ExpenseUpdateView.get_form` deletes the `installments` field that the create form added.

## Templates and JS (audit by subagent; B = `registers/templates/core/base.html`, C = `reports/templates/reports/components/`, J = `registers/static/js/`)

### F8. One small JS helper module owns fetch, CSRF and money formatting; endpoints come from `{% url %}`
`J/app.js` (loaded once in B) exports `postJSON`, `brl`. Each component reads its endpoints from `data-*-url` attributes rendered with `{% url %}`.
- 8 CSRF-cookie readers: `J/expense_payment.js:6`, `expense_list_page.js:12`, `recurring_expense_list.js:72`, `category_autocomplete.js:332`, `recent_expenses.js:379`, `recent_incomes.js:236`, `register/quick_fill_preset_list.html:121`, `register/csv_processor_preview.html:324`.
- ~12 JS currency formatters (`Intl.NumberFormat`/`toLocaleString`) in five card templates, both chart partials, `daily_spending_chart.js`, `category_table.js`, `expense_list_page.js`.
- Endpoints hard-coded in JS: `daily_spending_chart.js:232,455`, `category_table.js:424`, `recent_expenses.js:16-19,164,196`, `recent_incomes.js:14-16`, `category_autocomplete.js:9-10`, `recurring_expense_list.js:8,46`, `expense_list_page.js:24`, `quick_fill_preset_list.html:143`.
- The `/despesas/lista/` query contract is built by hand in `C/daily_total_card.html:2`, `C/installment_monthly_card.html:3`, `daily_spending_chart.js:454`, `category_table.js:423`, `recent_expenses.js:195`.

### F9. Data reaches JS as numbers through `json_script`; the server formats display text
- Five summary-card inline scripts re-format text `format_brl` already rendered; `category_table.js:9-11` parses formatted strings back (breaks ≥ R$ 1.000.000) and compares `'R$ 0,00'` (`:347,473`).
- Chart data dumped as Python repr through `|safe` (`C/expense_income_chart.html:26`, `C/payment_method_chart.html:31`, `register/csv_processor_preview.html:133`); key `datasets` in one chart, `data` in the other.
- `CategoryTableConfig` is a hand-built JS literal (`C/expense_category_table.html:62-70`, `year|default:2024`, untranslated months); data arrives by two mechanisms.
- Daily chart: day options in the template must match `ajax.py` validation, the JS default and `dashboard.py`; the outlier threshold 1000 is copied into a label; mobile re-fetches 7 days right after the server rendered 30; `#debugInfo` panel and `console.log`s left in.
- Two near-identical horizontal bar chart partials; Chart.js + datalabels loaded twice on the Resumo tab; CDN scripts unversioned.

### F10. base.html owns the page chrome
- Flash messages are rendered by 11 templates in 3 styles and never by B; `recurring_expense_list.html` has none, so the success messages after create/update are lost.
- 11 copies of the nav-link class string; active state by path substring (`'export' in request.path`); B:48 and B:72 re-test `'dashboard_'` url names.
- The bell markup exists in B:73-80 and `C/payment_notifications_toggle.html` with the same ids; `C/filter_form.html:6` (a filter) includes the bell.
- `auth/login.html` repeats B's head; `core/index.html` never referenced; `S/custom.css` is a one-line comment; `?v=` cache-buster redundant with the manifest storage.

### F11. One template per entity form, one "recent items" component, one CSV input partial
- `register/recurring_expense_form.html:18-65` ≈ `reports/recurring_expense_update.html:20-67`; `register/expense_form.html:40-74` ≈ `reports/expense_update.html:15-34`; `register/csv_import.html` ≈ `register/csv_processor.html` (input half + JS); `recent_expenses.js` ≈ `recent_incomes.js` and their table partials.
- `recent_expenses.js` dead modal code (`#expenseDetailsModal` doesn't exist) and "View details" throws (`this.expenses` never assigned); `expense_details_ajax` has no working caller.
- 24 copies of `add_class` Tailwind strings across 6 templates while CSV forms set other (light-theme) classes in Python.
- `register/budget_estimate_list.html:22-33` hard-codes 12 month options; five month/year picker variants.
- csv templates test `startsWith('Selected:')` against a translated string.

### F12. Dead front-end code
- `category_table.js:160-193,366-396` (selectors that match nothing), `data-*` attributes written and never read, `window.showExpenseDetailsForDate`, `data-active`, `installmentMonthlyCardRoot` ids, unused `{% load static %}`, `register/csv_import_preview.html:342-349` branches identical to `else`, `recent_incomes.js:172-174` unreachable fallback, `get_item` in `currency_filters.py` (copy of `custom_filters.get_item`), `C/payment_checkbox.html:2` csrf token never read.
- `setTimeout` sequencing: `category_table.js:510,514`, `recurring_expense_list.js:58` (reload after 500 ms), `csv_processor_preview.html:314` (download after a 500 ms "wait" for the sync, whose failure is swallowed).

## Behavior changes that come with the fixes (intended)
- Every report, list and edit view is scoped to the logged-in user. Production's `testuser` (2 expenses, Jan/2025) no longer counts in the owner's totals. Another user's record now answers 404 (JSON endpoints: `{"error": …}`) instead of 403.
- Recurring generation clamps the day to the month's end (day 31 → Feb 28/29) everywhere; before, the process page reported an error, the command skipped, and only the sync clamped. "Already generated" means any expense of that schedule in the same calendar month (before: same exact date, so an edited date produced a duplicate).
- `recurrence_payment` uses the same rule (it already processed every user).
- Creating a recurring expense keeps `is_international` (the old service dropped it, losing IOF).
- The expense description is limited to the model's 100 characters by the form (before: 200 in the form, database error on PostgreSQL).
- Bad `?month=`/`?year=` on dashboard tabs, budget estimates and export answer 400 instead of 500.
- CSV: a blank `type` cell falls back to the amount's sign (before: row error); a blank category uses the default instead of creating a category called "nan"; pasted text must contain the chosen separator (before: `|` was offered but rejected).
- `format_brl` follows Intl's pt-BR currency format, like the inline scripts it replaced: sign before the symbol (`-R$ 42.161,82`, before: `R$ -42.161,82` from the server) and a no-break space, so an amount never wraps between `R$` and the number. Summary-card amounts scale with the card (`13cqi`, 16–28px) so a 14-character amount stays on one line in the 7-column row.
- Month names on charts and in the category table are translated (before: English `calendar.month_name`); the heat-map now reads real numbers (before: it parsed formatted strings and broke above R$ 1.000.000).
- Flash messages show on every page, at the top (before: some pages never showed them, e.g. after creating a recurring expense).
- Recent expenses/incomes are rendered with the page instead of fetched by AJAX; the income list uses the same action menu as expenses. Their autofill/details/list endpoints are gone.
- The recurring list reloads after toggle/delete, so the active/inactive groups are right (before: only the icon changed).

- CSV import: the "Skip Header Row" option (on by default) is gone. pandas already reads the header, so the option silently dropped the first record of every default import (a one-row file came back "empty").
- CSV previews turn blanks (NaN/NaT) into empty cells: an invalid date no longer crashes the import preview (500), and a blank Nubank amount no longer breaks the processor preview's script.
- Strings in the CSV pages' JS are rendered by the templates (translatable); the `jsi18n` catalog had no `djangojs` translations, so they were always English. The catalog view and its script tag are gone.

## Second round (subagent audits after F1–F12)
Fixed:
- One definition of "a recurring expense due in a month" (`RecurringExpense.objects.due_in`) for generation, the command, the month overview and the fixed totals; totals include IOF (`charged_total`) like the generated expenses. Generating a month before a schedule's start no longer creates an expense.
- Form errors: every field renders through `form_field.html` with its own errors, form-wide errors through `form_errors.html`; views no longer flash field errors. Fixes the income form losing all errors but the category's, CSV errors shown twice, and `__all__` printed on the estimate pages.
- Estimates: month/year validated by the form (1–12, 2000–2100) and duplicates checked in `clean()`, so editing onto an existing category/month shows an error instead of a 500.
- The expense form offers expense categories only (the model's own rule); categories and payment methods are ordered by name in Meta (migration 0016, no SQL). Income amounts accept "12,50" like expenses.
- Delete confirmation of an estimate whose category has an apostrophe no longer skips the question (inline JS replaced by `<form data-confirm>`); POST buttons show the server's error instead of failing silently; the expense list reloads after a delete so every total is right.
- CSV processor warnings shown once; empty cells stay empty (placeholder via CSS) instead of saving "-".
- `json_object()` parses JSON bodies for every endpoint (a JSON list no longer 500s); recurring delete/toggle answer JSON 404s; the CSV confirm step reuses the import parser; unexpected row errors keep their traceback in the log; MCP reports unknown tools with its own exception.
- Shared template tags moved to the `utils` app; `format_brl` renders blank instead of a believable "R$ 0,00" for non-numbers; sidebar highlights CSV and edit pages; budget breakdown no longer runs the dashboard filter queries; dead cache settings and unread ids/classes removed.

Left, with reasons:
- Expense/recurring edit views stay in `reports` while create views are in `registers`: moving them changes URLs (`/expense/<id>/update/`, `/recurring-expense/<id>/…`) that bookmarks and the UI tests use; they share the form and template already.
- `overall_progress` divides spending in estimated categories by fixed + installments + estimates: a product question (what the bar should show), not structure.
- Hard-coded Portuguese strings next to translated ones (tab labels, payments pages, list titles): making them translatable is i18n work beyond this refactor.
- Desktop table + mobile card markup per list page, two occurrence-row partials, `next`/`back` return parameters, five month/year picker layouts, the unpinned Tailwind CDN: minor, each needs a design decision.

## Third round (final audit)
Fixed: the CSV import confirm asked twice (and a "no" left the button stuck); logout was a GET link that Django 5 answers with 405 — now a POST form; `LOGGING` disabled Django's own loggers so production 500s were never logged; a CSV of only blank rows passed the preview and crashed on confirm; services took `(month, year)` while models took `(year, month)` — one order now, `(year, month)`, everywhere (a swapped call silently queried the wrong period); the fields a recurring occurrence copies are listed once; year inputs get their bounds from `YEAR_RANGE` (`{% year_bounds %}`; one copy said 2020); the site chrome (base, login, sidebar tag, app.js, shared CSS) moved to project-level `templates/` and `static/`, so `registers` and `reports` templates no longer depend on each other both ways.
Left: the IOF rate is repeated in the recurring form's label text — building a localized, lazily translated label from `IOF_RATE` costs more than editing one string when the decree changes.

## Fourth round (confirmation audit)
Fixed: unhandled errors are now logged with DEBUG=False (root console handler at ERROR; Django's own console handler only prints in DEBUG); the import confirmation's spinner runs after app.js's `data-confirm`, so answering "no" leaves the button usable; creating a schedule from an expense lives on the model next to its inverse (`RecurringExpense.start_from`); recurring rows and not-yet-generated schedules show the charged amount (IOF included), matching the totals; the shared dialog look moved to `static/css/dialog.css` (`.app-dialog`); the last private helpers take (year, month).
The audit found nothing else: every template/static path resolves, every template's context variables exist, every msgid is translated, and no code is unused.

## Kept on purpose
- `reports.models.BillingPeriod`: nothing reads it, but production has 16 rows in its table; dropping it needs a migration that deletes data — left for the owner to decide.
- `'Investimento'` excluded from the spending charts by name (`reports/services/summary.py`): the system needs it, and a flag on PaymentMethod would need a schema + data migration.
- `settings.py` `if "test" not in sys.argv` for the manifest storage: tests run without `collectstatic`.
- `docs/superpowers/` plans/specs mention the old layers: historical records, not instructions.
- Calendar month vs billing month: lists of "what happened" (Despesas tab, export, recurring due dates, installment progress) use the calendar month; bills and budgets use the billing month. Both are named in `ExpenseQuerySet` (`in_month`, `in_billing_month`).
