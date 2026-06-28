from django.urls import path
from . import views

urlpatterns = [
    path('expense', views.expense_export, name='expense_export'),
]
