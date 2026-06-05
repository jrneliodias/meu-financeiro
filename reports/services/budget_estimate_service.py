from decimal import Decimal
from reports.dataclasses import BudgetEstimateItem, BudgetSummary
from reports.repository.budget_estimate_repository import BudgetEstimateRepository
from reports.repository.recurring_expense_repository import RecurringExpenseRepository


class BudgetEstimateService:
    def __init__(self):
        self._repo = BudgetEstimateRepository()
        self._recurring_repo = RecurringExpenseRepository()

    def get_monthly_budget_summary(self, user, month: int, year: int) -> BudgetSummary:
        estimates = self._repo.get_estimates_with_actuals(user, month, year)
        total_fixed = self._recurring_repo.get_total_recurring_expenses_with_debit(user)

        items = []
        total_estimated = Decimal('0')
        for est in estimates:
            progress = float(est.actual_amount / est.amount * 100) if est.amount else 0.0
            items.append(BudgetEstimateItem(
                category_name=est.category.name,
                estimated_amount=est.amount,
                actual_amount=est.actual_amount,
                progress_percentage=min(progress, 999.0),
                is_over_budget=progress > 100,
            ))
            total_estimated += est.amount

        total_actual = Decimal(str(sum(float(i.actual_amount) for i in items)))
        total_expected = total_fixed + total_estimated
        overall_progress = float(total_actual / total_expected * 100) if total_expected else 0.0

        return BudgetSummary(
            estimates=items,
            total_estimated=total_estimated,
            total_fixed=total_fixed,
            total_expected=total_expected,
            total_actual=total_actual,
            overall_progress=overall_progress,
        )
