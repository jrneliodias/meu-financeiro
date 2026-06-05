from decimal import Decimal
from django.db.models import Sum, OuterRef, Subquery
from django.db.models.functions import Coalesce
from registers.models import CategoryBudgetEstimate, Expense


class BudgetEstimateRepository:
    def get_estimates_with_actuals(self, user, month: int, year: int):
        actual_subquery = (
            Expense.objects
            .filter(user=user, date__month=month, date__year=year, category=OuterRef('category'))
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
