
from django.urls import path
from . import views


urlpatterns = [
    path("expense", views.register_expense,
         name="register_expense"),
    path("expense/success", views.expense_success, name="expense_success"),
    path("expense/recent/", views.recent_expenses_ajax, name="recent_expenses_ajax"),
    path("expense/<int:pk>/details/", views.expense_details_ajax, name="expense_details_ajax"),
    path("expense/<int:pk>/autofill/", views.expense_autofill_ajax, name="expense_autofill_ajax"),
    path("expense/list-details/", views.expense_list_details_ajax, name="expense_list_details_ajax"),
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
    # Quick Fill Preset CRUD
    path("quick-fill-presets/", views.quick_fill_preset_list, name="quick_fill_preset_list"),
    path("quick-fill-presets/create/", views.quick_fill_preset_create, name="quick_fill_preset_create"),
    path("quick-fill-presets/<int:pk>/edit/", views.quick_fill_preset_edit, name="quick_fill_preset_edit"),
    path("quick-fill-presets/<int:pk>/delete/", views.quick_fill_preset_delete, name="quick_fill_preset_delete"),
    # Category autocomplete
    path("categories/search/", views.category_search_ajax, name="category_search_ajax"),
    path("categories/create/", views.category_create_ajax, name="category_create_ajax"),
    # Budget Estimates CRUD
    path("estimativas/", views.budget_estimate_list, name="budget_estimate_list"),
    path("estimativas/<int:pk>/editar/", views.budget_estimate_update, name="budget_estimate_update"),
    path("estimativas/<int:pk>/excluir/", views.budget_estimate_delete, name="budget_estimate_delete"),
]
