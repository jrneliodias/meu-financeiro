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
