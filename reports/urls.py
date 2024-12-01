
from django.urls import path
from . import views

urlpatterns = [
    path("", views.expense_report, name="expense_report"),
    path("expense/<int:pk>/update/",
         views.ExpenseUpdateView.as_view(), name="expense_update"),
]
