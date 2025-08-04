
from django.urls import path
from . import views


urlpatterns = [
    path("expense", views.register_expense,
         name="register_expense"),
    path("expense/success", views.expense_success, name="expense_success"),
    path("income", views.register_income,
         name="register_income"),
    path("csv-import", views.csv_import, name="csv_import"),
    path("csv-import/confirm", views.csv_import_confirm, name="csv_import_confirm"),
    path("csv-import/ajax", views.csv_import_ajax, name="csv_import_ajax"),
]
