
from django.urls import path
from . import views

urlpatterns = [
    path("register/expense", views.register_expense,
         name="register_expense"),
    path("register/sucess", views.expense_success, name="expense_success"),
    path("register/income", views.register_income,
         name="register_income"),
]
