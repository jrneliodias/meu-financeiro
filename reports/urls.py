from django.urls import path

from .views import ajax, dashboard, expense_list, expense_update, recurring

urlpatterns = [
    path("", dashboard.expense_report, name="expense_report"),
    path("gastos/", dashboard.spending, name="dashboard_spending"),
    path("categorias/", dashboard.categories, name="dashboard_categories"),
    path("parcelas/", dashboard.installments, name="dashboard_installments"),
    path("despesas/", dashboard.expenses, name="dashboard_expenses"),
    path("orcamento/detalhamento/", dashboard.budget_breakdown, name="budget_breakdown"),
    path("daily-spending-data/", ajax.daily_spending_data_ajax, name="daily_spending_data_ajax"),
    path("despesas/lista/", expense_list.expense_list_page, name="expense_list_page"),
    path("expense/<int:pk>/update/", expense_update.ExpenseUpdateView.as_view(), name="expense_update"),
    path("payment-notifications/", recurring.payment_notifications, name="payment_notifications"),
    path("recurring-payments/", recurring.recurring_payments, name="recurring_payments"),
    path("recurring-expenses/", recurring.recurring_expense_list, name="recurring_expense_list"),
    path("recurring-expenses/processar/", recurring.recurring_expense_process, name="recurring_expense_process"),
    path("recurring-expense/<int:pk>/update/", recurring.RecurringExpenseUpdateView.as_view(),
         name="recurring_expense_update"),
    path("recurring-expense/<int:pk>/delete/", recurring.recurring_expense_delete, name="recurring_expense_delete"),
    path("recurring-expense/<int:pk>/toggle/", recurring.recurring_expense_toggle, name="recurring_expense_toggle"),
    path("recurring-expense/<int:expense_id>/payment/", recurring.recurring_expense_set_paid,
         name="recurring_expense_set_paid"),
    path("recurring-expense/<int:pk>/expenses/", recurring.recurring_expense_expenses,
         name="recurring_expense_expenses"),
]
