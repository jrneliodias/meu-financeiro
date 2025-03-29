from reports.dataclasses import CategoryExpense
from typing import List


class CategoryExpenseCalculator:
    def __init__(self, expense_repository, billing_calculator):
        self.expense_repository = expense_repository
        self.billing_calculator = billing_calculator

    def calculate_monthly_expenses(self, payment_method, month: int, year: int) -> List[CategoryExpense]:
        """Calculate expenses by category for a specific month and payment method."""
        period = self.billing_calculator.calculate_period(
            month, payment_method.start_billing_day)

        expenses = self.expense_repository.get_expenses_by_category_in_period(
            payment_method=payment_method,
            start_date=period.start_date,
            end_date=period.end_date
        )

        return [
            CategoryExpense(
                name=expense['category__name'],
                amount=expense['total_amount'],
                payment_method=payment_method.name,
                month=period.billing_month
            )
            for expense in expenses
        ]
