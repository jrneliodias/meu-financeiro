from registers.models import Expense
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncYear, TruncDate

import calendar


class ExpenseRepository:

    def get_monthly_expenses_by_year(self, year, month):
        return (
            Expense.objects
            .filter(date__year=year)
            .filter(date__month=month)
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
        months_set = (
            Expense.objects
            .filter(date__year=year)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .distinct()
            .order_by('month')
        )
        return [(expense['month'].month, calendar.month_name[expense['month'].month])
                for expense in months_set]

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

    def get_months_by_year(self, year):
        months_set = (
            Expense.objects
            .filter(date__year=year)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .distinct()
            .order_by('month')
        )
        return [(expense['month'].month, calendar.month_name[expense['month'].month])
                for expense in months_set]

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
        """Retrieve distinct months from the database."""
        distinct_months = (
            Expense.objects
            .annotate(month=TruncMonth('date'))
            .values('month')
            .distinct()
            .order_by('month')
        )
        months_list = [calendar.month_name[expense['month'].month]
                       for expense in distinct_months]
        return months_list

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
                'created_at'
            )
            .order_by('-amount', 'description')  # Highest amounts first
        )
