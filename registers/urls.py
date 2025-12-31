
from django.urls import path
from . import views


urlpatterns = [
    path("expense", views.register_expense,
         name="register_expense"),
    path("expense/success", views.expense_success, name="expense_success"),
    path("expense/<int:pk>/delete/", views.delete_expense, name="delete_expense"),
    path("income", views.register_income,
         name="register_income"),
    path("recurring-expense", views.register_recurring_expense,
         name="register_recurring_expense"),
    path("csv-import", views.csv_import, name="csv_import"),
    path("csv-import/confirm", views.csv_import_confirm, name="csv_import_confirm"),
    path("csv-import/ajax", views.csv_import_ajax, name="csv_import_ajax"),
    path("csv-processor", views.csv_processor, name="csv_processor"),
    path("csv-processor/download", views.csv_processor_download, name="csv_processor_download"),
    path("csv-processor/update", views.csv_processor_update_data, name="csv_processor_update_data"),
]
