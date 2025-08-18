
from django.urls import path
from . import views

urlpatterns = [
    path("", views.expense_report, name="expense_report"),
    path("expense/<int:pk>/update/",
         views.ExpenseUpdateView.as_view(), name="expense_update"),
    path("daily-spending-data/", views.daily_spending_data_ajax, name="daily_spending_data_ajax"),
    path("expense-details/", views.expense_details_ajax, name="expense_details_ajax"),
]
