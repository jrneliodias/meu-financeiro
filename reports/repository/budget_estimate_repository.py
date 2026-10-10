from decimal import Decimal
from django.db.models import Sum, OuterRef, Subquery
from django.db.models.functions import Coalesce
from registers.models import CategoryBudgetEstimate
from reports.repository.expense_repository import expenses_in_billing_month


class BudgetEstimateRepository:
    def get_estimates_with_actuals(self, user, month: int, year: int):
        actual_subquery = (
            expenses_in_billing_month(year, month)
            .filter(user=user, category=OuterRef('category'))
            .values('category')
            .annotate(total=Sum('amount'))
            .values('total')
        )
        return (
            CategoryBudgetEstimate.objects
            .filter(user=user, month=month, year=year)
            .select_related('category')
            .annotate(actual_amount=Coalesce(Subquery(actual_subquery), Decimal('0')))
            .order_by('category__name')
        )
