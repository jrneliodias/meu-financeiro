from registers.models import Expense
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncYear, TruncDate
from decimal import Decimal

import calendar


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

    def get_expenses_by_date(self, target_date):
        """
        Get all expenses for a specific date with related category and payment method data.
        
        Returns detailed expense information for modal display:
        - Individual expense records (not aggregated)
        - Category and payment method names via joins
        - Ordered by amount (highest first) for better UX
        
        Why this design?
        1. Single date focus - optimized for modal use case
        2. Full expense details - description, amount, category, payment method
        3. Efficient joins - avoid N+1 queries
        4. User-friendly ordering - most expensive items first
        """
        return (
            Expense.objects
            .filter(date=target_date)
            .select_related('category', 'payment_method')  # Efficient joins
            .values(
                'id',
                'description',
                'amount',
                'category__name',
                'payment_method__name',
                'created_at',
                'reccurring_expense_id',
                'installment_plan_id',
            )
            .order_by('-amount', 'description')  # Highest amounts first
        )

    def get_recurring_total_by_date(self, target_date):
        result = (
            Expense.objects
            .filter(date=target_date, reccurring_expense__isnull=False)
            .aggregate(total=Sum('amount'))
        )
        return result['total'] or 0

    def get_installment_total_by_date(self, target_date):
        result = (
            Expense.objects
            .filter(date=target_date, installment_plan__isnull=False)
            .aggregate(total=Sum('amount'))
        )
        return result['total'] or 0

    def get_category_totals_by_date(self, target_date):
        return (
            Expense.objects
            .filter(date=target_date)
            .values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

    def get_total_by_date(self, target_date):
        """Return the total sum of all expenses for a specific date."""
        result = Expense.objects.filter(date=target_date).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')

    def get_expenses_by_category_and_month(
        self,
        target_year: int,
        target_month_number: int,
        category_name_filter: str
    ):
        """
        Get all expenses for a specific category and month with related data.

        Single Responsibility: This method only retrieves expense data.
        It does NOT format, validate, or transform the data.

        Args:
            target_year: Year to filter expenses (e.g., 2024)
            target_month_number: Month number (1-12, where 1=January, 12=December)
            category_name_filter: Category name to filter by (e.g., "Groceries")

        Returns:
            QuerySet containing expense records with related category and payment method data.
            Each record includes: id, date, description, amount, category name, payment method name, created_at.
            Results are ordered chronologically by date, then by amount (highest first) within each day.

        Performance:
            - Uses select_related() to avoid N+1 queries
            - Single optimized database query with JOIN operations
            - Only fetches required fields via values()
        """
        expense_queryset_with_relations = (
            Expense.objects
            .filter(
                date__year=target_year,
                date__month=target_month_number,
                category__name=category_name_filter
            )
            .select_related('category', 'payment_method')  # Eager loading to prevent N+1 queries
            .values(
                'id',
                'date',
                'description',
                'amount',
                'category__name',
                'payment_method__name',
                'created_at'
            )
            .order_by('date', '-amount')  # Chronological, then highest amounts first
        )

        return expense_queryset_with_relations

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
            Expense.objects
            .filter(date__year=year)
            .annotate(month=TruncMonth('date'))
            .values('month', 'category__name')
            .annotate(total_amount=Sum('amount'))
            .order_by('month', 'category__name')
        )

    def get_optimized_payment_method_expenses_by_month(self, year):
        """
        OPTIMIZED: Single query to get payment method expenses by month.
        
        Consolidates multiple payment method queries into efficient aggregations.
        Performance: ~12+ queries reduced to 1 query
        """
        return (
            Expense.objects
            .filter(date__year=year)
            .annotate(month=TruncMonth('date'))
            .values('month', 'payment_method__name')
            .annotate(total_amount=Sum('amount'))
            .order_by('month', 'payment_method__name')
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
