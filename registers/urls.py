from django.urls import path

from .views import budget_estimates, categories, csv_import, csv_processor, expenses, incomes, presets, recurring

urlpatterns = [
    path("expense", expenses.register_expense, name="register_expense"),
    path("expense/<int:pk>/delete/", expenses.delete_expense, name="delete_expense"),
    path("income", incomes.register_income, name="register_income"),
    path("income/<int:pk>/delete/", incomes.delete_income, name="delete_income"),
    path("recurring-expense", recurring.register_recurring_expense, name="register_recurring_expense"),
    path("csv-import", csv_import.csv_import, name="csv_import"),
    path("csv-import/confirm", csv_import.csv_import_confirm, name="csv_import_confirm"),
    path("csv-processor", csv_processor.csv_processor, name="csv_processor"),
    path("csv-processor/download", csv_processor.csv_processor_download, name="csv_processor_download"),
    path("csv-processor/update", csv_processor.csv_processor_update_data, name="csv_processor_update_data"),
    path("quick-fill-presets/", presets.quick_fill_preset_list, name="quick_fill_preset_list"),
    path("quick-fill-presets/create/", presets.quick_fill_preset_create, name="quick_fill_preset_create"),
    path("quick-fill-presets/<int:pk>/edit/", presets.quick_fill_preset_edit, name="quick_fill_preset_edit"),
    path("quick-fill-presets/<int:pk>/delete/", presets.quick_fill_preset_delete, name="quick_fill_preset_delete"),
    path("categories/search/", categories.category_search_ajax, name="category_search_ajax"),
    path("categories/create/", categories.category_create_ajax, name="category_create_ajax"),
    path("estimativas/", budget_estimates.budget_estimate_list, name="budget_estimate_list"),
    path("estimativas/<int:pk>/editar/", budget_estimates.budget_estimate_update, name="budget_estimate_update"),
    path("estimativas/<int:pk>/excluir/", budget_estimates.budget_estimate_delete, name="budget_estimate_delete"),
    path("estimativas/copiar/", budget_estimates.budget_estimate_copy, name="budget_estimate_copy"),
]
