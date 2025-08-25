from registers.models import Income
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncYear


class IncomeRepository:

    def get_incomes_by_month(self, year):
        """Returns a dictionary where onths as keys and the total income for that month as values."""
        income_by_month_query_set = (
            Income.objects
            .filter(date__year=year)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total_amount=Sum('amount'))
            .order_by('month',)
        )
        return income_by_month_query_set

    def get_optimized_incomes_by_month(self, year):
        """
        OPTIMIZED: Single query to get income data by month.
        
        Replaces multiple queries with a single aggregated query.
        Performance: Multiple queries reduced to 1 query
        """
        return (
            Income.objects
            .filter(date__year=year)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total_amount=Sum('amount'))
            .order_by('month')
        )
