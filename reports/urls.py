
from django.urls import path
from . import views

urlpatterns = [
    path("", views.expense_report, name="expense_report"),
    path("expense/<int:pk>/update/",
         views.ExpenseUpdateView.as_view(), name="expense_update"),
    path("recurring-expenses/", views.recurring_expense_list, name="recurring_expense_list"),
    path("recurring-expense/<int:pk>/update/",
         views.RecurringExpenseUpdateView.as_view(), name="recurring_expense_update"),
    path("recurring-expense/<int:pk>/delete/",
         views.recurring_expense_delete, name="recurring_expense_delete"),
    path("recurring-expense/<int:pk>/toggle/",
         views.recurring_expense_toggle, name="recurring_expense_toggle"),
    path("recurring-expense-details/",
         views.recurring_expense_details_ajax, name="recurring_expense_details_ajax"),
    path("process-recurring-expenses/",
         views.process_recurring_expenses_ajax, name="process_recurring_expenses_ajax"),
    path("daily-spending-data/", views.daily_spending_data_ajax, name="daily_spending_data_ajax"),
    path("expense-details/", views.expense_details_ajax, name="expense_details_ajax"),
    path("category-expense-details/", views.category_expense_details_ajax, name="category_expense_details_ajax"),
]
