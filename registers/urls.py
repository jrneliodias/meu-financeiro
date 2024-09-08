
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("register/expense", views.register_expense,
         name="register_expense"),
    path("register/sucess", views.expense_success, name="expense_success"),
]
