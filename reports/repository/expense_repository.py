from registers.models import Expense
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncYear

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
