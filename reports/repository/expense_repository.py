from registers.models import Expense
from django.db.models import Sum, Case, When, F, Q
from django.db.models.functions import TruncMonth, TruncYear, TruncDate, ExtractDay, ExtractMonth, ExtractYear
from datetime import date
from decimal import Decimal

import calendar


def with_billing_month(queryset):
    """
    Annotate billing_year/billing_month: an expense dated before its payment
    method's start_billing_day belongs to the previous month's bill
    (start day 3 → Oct 3..Nov 2 is October).
    """
    before_start = Q(date__day__lt=F('payment_method__start_billing_day'))
    return queryset.annotate(
        billing_month=Case(
            When(before_start & Q(date__month=1), then=12),
            When(before_start, then=ExtractMonth('date') - 1),
            default=ExtractMonth('date'),
        ),
        billing_year=Case(
            When(before_start & Q(date__month=1), then=ExtractYear('date') - 1),
            default=ExtractYear('date'),
        ),
    )


def expenses_in_billing_year(year):
    # Billing year spills into early next year (e.g. Jan 1-2 → December bill).
    return with_billing_month(
        Expense.objects.filter(date__gte=date(year, 1, 1), date__lt=date(year + 1, 2, 1))
    ).filter(billing_year=year)


def expenses_in_billing_month(year, month, queryset=None):
    # Bill of month M only holds expenses dated in M or M+1.
    range_end = date(year + 1, 2, 1) if month == 12 else date(year + (month + 1) // 12, (month + 1) % 12 + 1, 1)
    return with_billing_month(
        (queryset if queryset is not None else Expense.objects)
        .filter(date__gte=date(year, month, 1), date__lt=range_end)
    ).filter(billing_year=year, billing_month=month)


class ExpenseRepository:

    def get_monthly_expenses_by_year(self, year, month):
        return (
            Expense.objects
            .filter(date__year=year, date__month=month)
            .select_related('category', 'payment_method', 'reccurring_expense')  # Avoid N+1 queries
            .order_by('date')
        )

    def get_total_payment_method_expenses_by_filter(self, payment_method, start_date, end_date):

        return (
            Expense.objects.filter(
                payment_method=payment_method,
                date__gte=start_date,
                date__lte=end_date
            )
            .aggregate(total=Sum('amount'))['total']
        )

    def get_expenses_by_filter(self, filter):
        start_date = filter.get('start_date', None)
        end_date = filter.get('end_date', None)
        values = filter.get('values', None)

        credit_expenses = (
            Expense.objects
            .filter(  # Credit card payments start on 24th
                date__gte=start_date,
                date__lte=end_date,
            )
            .values(values)
            .annotate(total_amount=Sum('amount'))
        )

        return credit_expenses

    def get_months_by_year(self, year):
        """
        OPTIMIZED: Return all 12 months instead of querying database.
        This eliminates an unnecessary query and provides consistent month options.
        """
        return [(month, calendar.month_name[month]) for month in range(1, 13)]

    def get_monthly_expenses_by_payment_method(self, year: int):

        expenses_by_payment = (
            Expense.objects
            .filter(date__year=year)
            .annotate(month=TruncMonth('date'))
            .values('month', 'payment_method__name')
            .annotate(total_amount=Sum('amount'))
            .order_by('month', 'payment_method__name')
        )

        return list(expenses_by_payment)

    def get_distinct_years_in_tuples(self):
        """Returns distinct years from the Expense model."""
        distinct_years = (
            Expense
            .objects
            .annotate(year=TruncYear('date'))
            .values('year')
            .distinct()
            .order_by('year')
        )
        return [(expense['year'].year, expense['year'].year) for expense in distinct_years]

    def get_distinct_months_in_tuples(self):
        """Returns distinct months from the Expense model."""
        distinct_months = (
            Expense.objects
            .annotate(month=TruncMonth('date'))
            .values('month')
            .distinct()
            .order_by('month')
        )
        return [(expense['month'].month, calendar.month_name[expense['month'].month]) for expense in distinct_months]

    def get_months_in_list(self):
        """
        OPTIMIZED: Return all 12 month names instead of querying database.
        This eliminates an unnecessary query and provides consistent month options.
        """
        return [calendar.month_name[month] for month in range(1, 13)]

    def get_months_in_database(self):
        """Retrieve distinct months from the database."""
        _, months_processed = self.get_distinct_years_and_months()
        return [month[1] for month in months_processed]

    def get_expenses_for_year(self, year):
        """Fetch expenses for the given year, grouped by month and category."""
        return (
            Expense.objects
            .filter(date__year=year)
            .annotate(
                month=TruncMonth('date')
            )
            .values('month', 'category__name')
            .annotate(
                total_amount=Sum('amount')
            )
            .order_by('category__name', 'month')
        )

    def get_expenses_group_by_category_and_month(self, year, month):
        return (
            Expense.objects
            .filter(date__year=year, date__month=month)
            .values(
                'category__name'
            )
            .annotate(total_amount=Sum('amount'))
            .order_by('category__name')
        )

    def get_monthly_category_payment_method_total_expenses(self, year: int):

        expenses_by_payment = (
            Expense.objects
            .filter(date__year=year)
            .values('date', 'category__name', 'payment_method__name', 'amount')
            .order_by('category__name', 'date')
        )

        return list(expenses_by_payment)

    def get_expenses_by_category_in_period(self, payment_method, start_date, end_date):
        """Get expenses grouped by category for a specific period and payment method."""
        return Expense.objects.filter(
            payment_method=payment_method,
            date__gte=start_date,
            date__lte=end_date
        ).values('category__name').annotate(
            total_amount=Sum('amount')
        ).order_by('category__name')

    def get_daily_expenses_in_period(self, start_date, end_date, payment_method=None, category=None):
        """
        Get daily expense totals for a specific period with optional filters.
        
        Why this design?
        1. Flexible filtering while maintaining performance
        2. Database-level aggregation for efficiency
        3. Consistent with existing repository patterns
        4. Fixed SQLite compatibility issue with TruncDate by using date field directly
        """
        query = Expense.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        # Apply optional filters
        if payment_method:
            query = query.filter(payment_method=payment_method)
        if category:
            query = query.filter(category=category)
        
        return (
            query
            .values('date')  # Use date field directly instead of TruncDate
            .annotate(total_amount=Sum('amount'))
            .order_by('date')
        )

    def get_daily_expenses_by_category_in_period(self, start_date, end_date):
        """
        Get daily expenses broken down by category.
        Useful for stacked daily charts showing category breakdown.
        """
        return (
            Expense.objects
            .filter(date__gte=start_date, date__lte=end_date)
            .annotate(date_only=TruncDate('date'))
            .values('date_only', 'category__name')
            .annotate(total_amount=Sum('amount'))
            .order_by('date_only', 'category__name')
        )

    def get_daily_expenses_by_payment_method_in_period(self, start_date, end_date):
        """
        Get daily expenses broken down by payment method.
        """
        return (
            Expense.objects
            .filter(date__gte=start_date, date__lte=end_date)
            .annotate(date_only=TruncDate('date'))
            .values('date_only', 'payment_method__name')
            .annotate(total_amount=Sum('amount'))
            .order_by('date_only', 'payment_method__name')
        )

    def get_monthly_regular_expenses_total(self, month: int, year: int, user=None) -> Decimal:
        """Total de despesas avulsas no mês: exclui recorrentes e parcelas."""
        qs = expenses_in_billing_month(year, month).filter(
            installment_plan__isnull=True,
            reccurring_expense__isnull=True,
        )
        if user:
            qs = qs.filter(user=user)
        result = qs.aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')

    def get_total_by_date(self, target_date):
        """Return the total sum of all expenses for a specific date."""
        result = Expense.objects.filter(date=target_date).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')

    def get_expense_list(self, user, *, on_date=None, category_id=None,
                         installments=False, month=None, year=None, limit=None):
        """Despesas do usuário para a página de lista. Filtros: dia, ou mês de fatura
        (+ categoria e/ou só parcelas). Sem dia nem mês: mais recentes primeiro (use `limit`)."""
        has_period = on_date is not None or month is not None
        if on_date is not None:
            qs = Expense.objects.filter(date=on_date)
        elif month is not None:
            qs = expenses_in_billing_month(year, month)
        else:
            qs = Expense.objects.all()
        if category_id is not None:
            qs = qs.filter(category_id=category_id)
        if installments:
            qs = qs.filter(installment_plan__isnull=False)
        qs = (qs.filter(user=user)
              .select_related('category', 'payment_method', 'installment_plan', 'reccurring_expense')
              .order_by(*(('date', '-amount') if has_period else ('-date', '-amount'))))
        return qs[:limit] if limit else qs

    def get_optimized_expenses_by_month_and_category(self, year):
        """
        OPTIMIZED: Single aggregated query to get all expense data by category and month.
        
        Replaces the previous N×12 queries with a single database query using:
        - TruncMonth for efficient month grouping
        - Single aggregate with Sum() for totals
        - Proper handling of missing months with defaultdict
        
        Performance: ~50+ queries reduced to 1 query
        """
        return (
            expenses_in_billing_year(year)
            .values('billing_month', 'category__name')
            .annotate(total_amount=Sum('amount'))
            .order_by('billing_month', 'category__name')
        )

    def get_optimized_payment_method_expenses_by_month(self, year):
        """
        OPTIMIZED: Single query to get payment method expenses by month.
        
        Consolidates multiple payment method queries into efficient aggregations.
        Performance: ~12+ queries reduced to 1 query
        """
        return (
            expenses_in_billing_year(year)
            .values('billing_month', 'payment_method__name')
            .annotate(total_amount=Sum('amount'))
            .order_by('billing_month', 'payment_method__name')
        )

    def get_optimized_monthly_expenses_with_relations(self, year, month):
        """
        OPTIMIZED: Get monthly expenses with proper select_related to avoid N+1 queries.
        
        Performance: Eliminates N+1 queries by using select_related for foreign keys.
        """
        return (
            Expense.objects
            .filter(date__year=year, date__month=month)
            .select_related('category', 'payment_method', 'reccurring_expense')  # Avoid N+1 queries
            .order_by('date', '-amount')  # Order by date, then by amount descending
        )
