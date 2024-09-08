
from django.urls import path
from . import views

urlpatterns = [
    path("", views.expense_report, name="expense_report"),
]
