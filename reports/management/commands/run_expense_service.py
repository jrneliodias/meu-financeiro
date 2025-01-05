from django.core.management.base import BaseCommand
from reports.services import ExpenseService
from reports.repository.expense_repository import ExpenseRepository
from reports.repository.income_repository import IncomeRepository


class Command(BaseCommand):
    help = "Run Expense Service to get monthly expenses by category, payment method, and month."

    def handle(self, *args, **kwargs):
        expense_repository = ExpenseRepository()
        income_repository = IncomeRepository()
        expense_service = ExpenseService(expense_repository, income_repository)

        month_category_payment_method_total_expenses = expense_service.get_monthly_category_payment_method_total_expenses(
            2024
        )
