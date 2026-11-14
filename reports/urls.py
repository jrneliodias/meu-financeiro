
from django.urls import path
from . import views

urlpatterns = [
    path("payment-notifications/", views.payment_notifications, name="payment_notifications"),
    path("recurring-payments/", views.recurring_payments, name="recurring_payments"),
    path("", views.expense_report, name="expense_report"),
    path("orcamento/detalhamento/", views.budget_breakdown, name="budget_breakdown"),
    path("gastos/", views.spending, name="dashboard_spending"),
    path("categorias/", views.categories, name="dashboard_categories"),
    path("parcelas/", views.installments, name="dashboard_installments"),
    path("despesas/", views.expenses, name="dashboard_expenses"),
    path("despesas/lista/", views.expense_list_page, name="expense_list_page"),
    path("expense/<int:pk>/update/",
         views.ExpenseUpdateView.as_view(), name="expense_update"),
    path("recurring-expenses/", views.recurring_expense_list, name="recurring_expense_list"),
    path("recurring-expenses/processar/", views.recurring_expense_process, name="recurring_expense_process"),
    path("recurring-expense/<int:pk>/update/",
         views.RecurringExpenseUpdateView.as_view(), name="recurring_expense_update"),
    path("recurring-expense/<int:pk>/delete/",
         views.recurring_expense_delete, name="recurring_expense_delete"),
    path("recurring-expense/<int:pk>/toggle/",
         views.recurring_expense_toggle, name="recurring_expense_toggle"),
    path("recurring-expense/<int:expense_id>/payment/",
         views.recurring_expense_set_paid, name="recurring_expense_set_paid"),
    path("recurring-expense/<int:expense_id>/toggle-paid/",
         views.recurring_expense_toggle_paid, name="recurring_expense_toggle_paid"),
    path("recurring-expense/<int:pk>/expenses/",
         views.recurring_expense_expenses, name="recurring_expense_expenses"),
    path("daily-spending-data/", views.daily_spending_data_ajax, name="daily_spending_data_ajax"),
]
