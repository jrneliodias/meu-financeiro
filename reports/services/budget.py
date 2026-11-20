from dataclasses import dataclass
from decimal import Decimal
from typing import List

from django.db.models import OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from registers.models import CategoryBudgetEstimate, Expense, RecurringExpense

ZERO = Decimal('0')


@dataclass
class BudgetEstimateItem:
    category_name: str
    estimated_amount: Decimal
    actual_amount: Decimal
    progress_percentage: float
    is_over_budget: bool


@dataclass
class BudgetSummary:
    estimates: List[BudgetEstimateItem]
    total_estimated: Decimal
    total_fixed: Decimal
    total_installments: Decimal
    total_regular: Decimal
    total_actual: Decimal

    @property
    def total_expected(self):
        return self.total_fixed + self.total_installments + self.total_estimated

    @property
    def adjusted_expected(self):
        """Expected total plus what was already spent outside estimates, fixed and installments."""
        return self.total_expected + self.total_regular

    @property
    def overall_progress(self):
        total_expected = self.total_expected
        return float(self.total_actual / total_expected * 100) if total_expected else 0.0


def _total(queryset):
    return queryset.aggregate(total=Sum('amount'))['total'] or ZERO


def monthly_budget(user, year, month):
    """Fixed + installments + category estimates for the bill of month/year, against what was spent."""
    bill = Expense.objects.filter(user=user).in_billing_month(year, month)
    actual_by_category = (
        Expense.objects.filter(user=user, category=OuterRef('category')).in_billing_month(year, month)
        .values('category').annotate(total=Sum('amount')).values('total')
    )
    estimates = (
        CategoryBudgetEstimate.objects.filter(user=user, month=month, year=year)
        .select_related('category')
        .annotate(actual_amount=Coalesce(Subquery(actual_by_category), ZERO))
        .order_by('category__name')
    )
    items = []
    for estimate in estimates:
        progress = float(estimate.actual_amount / estimate.amount * 100) if estimate.amount else 0.0
        items.append(BudgetEstimateItem(
            category_name=estimate.category.name,
            estimated_amount=estimate.amount,
            actual_amount=estimate.actual_amount,
            progress_percentage=min(progress, 999.0),
            is_over_budget=progress > 100,
        ))
    return BudgetSummary(
        estimates=items,
        total_estimated=sum((item.estimated_amount for item in items), ZERO),
        total_fixed=RecurringExpense.objects.filter(user=user).due_in(year, month).charged_total(),
        total_installments=_total(bill.filter(installment_plan__isnull=False)),
        total_regular=_total(bill.filter(installment_plan__isnull=True, reccurring_expense__isnull=True)),
        total_actual=sum((item.actual_amount for item in items), ZERO),
    )
