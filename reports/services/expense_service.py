import json
from itertools import groupby
from operator import itemgetter
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from registers.models import PaymentMethod
import json
import calendar
from decimal import Decimal

from reports.services.billing_period_calculator import BillingPeriodCalculator
from reports.services.category_calculator import CategoryExpenseCalculator
from reports.services.expense_calculator import ExpenseCalculator
from reports.utils import convert_values_to_float, debug_to_json
from collections import defaultdict
from datetime import timedelta
from reports.dataclasses import CategoryExpense, MonthlyExpenseReport
from typing import List


class ExpenseService:
    def __init__(self, expense_repository, income_repository, billing_calculator=None, year=2024):
        self.expense_repository = expense_repository
        self.income_repository = income_repository
        self.year = year
        self.billing_calculator = billing_calculator or BillingPeriodCalculator(
            year)
        self.category_calculator = CategoryExpenseCalculator(
            expense_repository,
            self.billing_calculator
        )

        self.expense_calculator = ExpenseCalculator(
            expense_repository=self.expense_repository,
            year=self.year
        )

    def calculate_monthly_payment_method_total_expense_datasets(self):
        """Calculate monthly expenses datasets for all payment methods."""
        payment_methods = PaymentMethod.objects.all()
        labels = list(calendar.month_name)[1:]  # Skip empty first item
        datasets = []

        for payment_method in payment_methods:
            monthly_expenses = self.expense_calculator.calculate_monthly_expenses(
                payment_method,
                payment_method.start_billing_day
            )

            datasets.append({
                "label": payment_method.name,
                "data": [monthly_expenses[month] for month in labels],
            })

        debug_to_json(
            data={'labels': labels, 'datasets': datasets},
            filename_prefix='payment_method_datasets'
        )

        return {
            "labels": labels,
            "datasets": datasets,
        }

    def calculate_monthly_expenses_total(self):
        monthly_payment_method_expense_totals = self.calculate_monthly_payment_method_total_expense_datasets()

        # Debug input
        debug_to_json(
            data=monthly_payment_method_expense_totals,
            filename_prefix='monthly_expenses_total_input'
        )

        datasets = monthly_payment_method_expense_totals["datasets"]
        total_sum = [0]*len(datasets[0]["data"])

        # Debug calculation process
        calculation_steps = []
        for dataset in datasets:
            if dataset['label'] != 'Investimento':
                total_sum = [sum(x) for x in zip(total_sum, dataset["data"])]
                calculation_steps.append({
                    'payment_method': dataset['label'],
                    'data': dataset["data"],
                    'running_total': total_sum.copy()
                })

        # Debug output
        debug_to_json(
            data={
                'calculation_steps': calculation_steps,
                'final_total': total_sum
            },
            filename_prefix='monthly_expenses_total_calculation'
        )

        return {
            "labels": monthly_payment_method_expense_totals["labels"],
            "datasets": [{
                "label": "Total Expenses",
                "datasets": total_sum
            }]
        }

    def calculate_total_incomes_by_month(self):
        monthly_incomes_queryset = self.income_repository.get_incomes_by_month(
            self.year)
        monthly_incomes_dict = {income['month'].month: income['total_amount']
                                for income in monthly_incomes_queryset}
        all_months = list(range(1, 13))
        monthly_incomes_array = [float(monthly_incomes_dict.get(
            month, Decimal('0'))) for month in all_months]
        return {
            "label": "Total Income",
            "datasets": monthly_incomes_array
        }

    def create_month_total_datasets(self):
        monthly_expenses_total = self.calculate_monthly_expenses_total()
        monthly_incomes_income = self.calculate_total_incomes_by_month()

        monthly_expenses_total['datasets'].append(
            monthly_incomes_income)

        return monthly_expenses_total

    def get_total_expenses_amount_by_payment_method(self, payment_method, start_date, end_date):
        total_expenses = (
            self.expense_repository
            .get_total_payment_method_expenses_by_filter(
                payment_method, start_date, end_date
            )
        ) or Decimal('0')

        debug_to_json(
            data={
                'payment_method': payment_method.name,
                'start_date': start_date,
                'end_date': end_date,
                'total_expenses': total_expenses
            },
            filename_prefix=f'get_{payment_method.name}_total_expenses_amount_start_date_{start_date}_end_date_{end_date}'
        )
        return total_expenses

    def get_billing_month(self, day, start_date, end_date):
        return (
            start_date.strftime("%B")
            if day == 1 else
            end_date.strftime("%B")
        )

    def calculate_end_date(self, billing_day, month, year):
        if billing_day == 1:
            last_month_day = calendar.monthrange(year, month)[1]
            return date(year, month, last_month_day)

        if month == 12:
            # Handle transition to next year for December
            return date(year + 1, 1, billing_day - 1)

        return date(year, month + 1, billing_day - 1)

    def calculate_total_expense_for_payment_method(self, expenses_by_month, payment_method, billing_day):
        safe_filename = payment_method.name.replace(
            '/', '_').replace('\\', '_')
        debug_monthly_calculations = []

        # Debug input parameters
        debug_to_json(
            data={
                'initial_expenses_by_month': expenses_by_month,
                'payment_method': payment_method.name,
                'billing_day': billing_day,
            },
            filename_prefix=f'expense_calc_{safe_filename}'
        )

        for month in range(1, 13):
            # Calculate start date
            if month == 1:
                # January starts from December of previous year
                start_date = date(self.year - 1, 12, billing_day)
            else:
                start_date = date(self.year, month - 1, billing_day)

            # Calculate end date
            if billing_day == 1:
                # If billing day is 1, end date should be last day of the same month
                if month == 12:
                    end_date = date(self.year, 12, 31)  # December 31st
                else:
                    # Last day of the current month
                    next_month = month + 1
                    end_date = date(self.year, next_month,
                                    1) - timedelta(days=1)
            else:
                # Normal case: end date is the day before billing day
                if month == 12:
                    # December should end in the same year
                    end_date = date(self.year, 12, billing_day - 1)
                else:
                    end_date = date(self.year, month, billing_day - 1)

            total_expenses = self.get_total_expenses_amount_by_payment_method(
                payment_method, start_date, end_date)

            # The billing month is the current month
            billing_month = date(self.year, month, 1).strftime('%B')
            expenses_by_month[billing_month] += total_expenses

            # Debug each month's calculation
            debug_monthly_calculations.append({
                'month': month,
                'start_date': str(start_date),
                'end_date': str(end_date),
                'total_expenses': float(total_expenses),
                'billing_month': billing_month
            })

        # Debug final results
        debug_to_json(
            data={
                'monthly_calculations': debug_monthly_calculations,
                'final_expenses_by_month': expenses_by_month
            },
            filename_prefix=f'expense_calc_result_{safe_filename}'
        )

        return convert_values_to_float(expenses_by_month)

    def monthly_payment_method_expense_totals(self, year: int):
        payments_data = self.expense_repository.get_monthly_expenses_by_payment_method(
            year)

        payments_data.sort(key=itemgetter('month'))

        transformed_payments = []
        for month, items in groupby(payments_data, key=itemgetter('month')):
            month_name = month.strftime("%B")
            month_entry = {
                "month": month_name,
                "payment": [
                    {
                        "payment_method_name": item['payment_method__name'],
                        "total_amount": float(item['total_amount'])
                    }
                    for item in items
                ]
            }
            transformed_payments.append(month_entry)

        debug_to_json(
            data=transformed_payments,
            filename_prefix='expenses_by_payment'
        )

        return transformed_payments

    def get_monthly_category_payment_method_total_expenses(self, year: int):
        data = self.expense_repository.get_monthly_category_payment_method_total_expenses(
            year)

        full_formatted_data = defaultdict(
            lambda: defaultdict(lambda: defaultdict(Decimal)))

        # for item in data:
        #     category = item["category__name"]
        #     month = item["month"].strftime("%B")
        #     payment_method = item["payment_method__name"]
        #     total_amount = item["total_amount"]
        #     full_formatted_data[category][month][payment_method] += total_amount
        with open('expenses_by_category_payment.json', 'w', encoding='utf-8') as file:
            json.dump(data, file,
                      ensure_ascii=False, indent=4, cls=DjangoJSONEncoder)

        return full_formatted_data

    def get_expenses_by_category_and_payment_method(self) -> List[MonthlyExpenseReport]:
        """
        Calculate and format expenses by category and payment method for each month.
        Returns a list of MonthlyExpenseReport objects, each containing:
        - month name
        - list of categories with their expenses
        - total expenses for the month
        """
        # Get all payment methods
        payment_methods = PaymentMethod.objects.all()

        # Initialize data structure to collect expenses
        monthly_expenses = defaultdict(lambda: defaultdict(Decimal))
        monthly_payment_methods = defaultdict(lambda: defaultdict(list))

        # Calculate expenses for each month and payment method
        for month in range(1, 13):
            for payment_method in payment_methods:
                category_expenses = self.category_calculator.calculate_monthly_expenses(
                    payment_method, month, self.year
                )

                for expense in category_expenses:
                    monthly_expenses[expense.month][expense.name] += expense.amount
                    monthly_payment_methods[expense.month][expense.name].append({
                        'payment_method': expense.payment_method,
                        'amount': float(expense.amount)
                    })

                self._debug_category_calculation(
                    payment_method, month, category_expenses)

        # Format the results
        formatted_results = []
        for month in calendar.month_name[1:]:  # Skip empty first item
            if month in monthly_expenses:
                categories_data = []
                month_total = Decimal('0')

                for category, total in monthly_expenses[month].items():
                    category_data = {
                        'name': category,
                        'total_amount': float(total),
                        'payment_methods': monthly_payment_methods[month][category]
                    }
                    categories_data.append(category_data)
                    month_total += total

                formatted_results.append(MonthlyExpenseReport(
                    month=month,
                    categories=sorted(
                        categories_data, key=lambda x: x['name']),
                    total=month_total
                ))

        self._debug_final_results(formatted_results)
        return formatted_results

    def get_optimized_expenses_data(self, all_months):
        """
        OPTIMIZED: Get expense data by category and month using single query.
        
        Replaces the previous N×12 queries with a single database query.
        Performance: ~50+ queries reduced to 1 query
        """
        # Get data from repository
        expenses_by_month_category = self.expense_repository.get_optimized_expenses_by_month_and_category(self.year)
        
        # Initialize data structures with all months
        expenses_by_category_by_month = defaultdict(lambda: {month: 0.0 for month in all_months})
        total_expense_by_month = {month: 0.0 for month in all_months}
        
        # Process the single query result
        for item in expenses_by_month_category:
            month_name = item['month'].strftime('%B')
            category_name = item['category__name'] or 'No Category'
            amount = float(item['total_amount'])
            
            expenses_by_category_by_month[category_name][month_name] = amount
            total_expense_by_month[month_name] += amount
        
        return {
            'expenses_by_category_by_month': dict(expenses_by_category_by_month),
            'total_expense_by_month': total_expense_by_month
        }

    def get_optimized_incomes_by_month(self, all_months):
        """
        OPTIMIZED: Get income data by month using single query.
        
        Replaces multiple queries with a single aggregated query.
        Performance: Multiple queries reduced to 1 query
        """
        # Get data from repository
        incomes_by_month_query = self.income_repository.get_optimized_incomes_by_month(self.year)
        
        # Convert to dictionary with month names
        income_by_month_dict = {}
        for item in incomes_by_month_query:
            month_name = item['month'].strftime('%B')
            income_by_month_dict[month_name] = float(item['total_amount'])
        
        # Fill missing months with 0.0
        return {month: income_by_month_dict.get(month, 0.0) for month in all_months}

    def get_optimized_payment_method_data(self):
        """
        OPTIMIZED: Get payment method data and create datasets using single query.
        
        Consolidates multiple payment method queries into efficient aggregations.
        Performance: ~12+ queries reduced to 2-3 queries
        """
        # Get data from repositories
        payment_method_expenses = self.expense_repository.get_optimized_payment_method_expenses_by_month(self.year)
        income_by_month = self.income_repository.get_optimized_incomes_by_month(self.year)
        
        # Process payment method data
        monthly_totals = []
        payment_method_datasets = defaultdict(lambda: [0.0] * 12)
        
        # Group by month for monthly totals format
        monthly_data = defaultdict(list)
        for item in payment_method_expenses:
            month_name = item['month'].strftime('%B')
            month_index = item['month'].month - 1  # 0-based index for arrays
            payment_method = item['payment_method__name'] or 'No Payment Method'
            amount = float(item['total_amount'])
            
            monthly_data[month_name].append({
                'payment_method_name': payment_method,
                'total_amount': amount
            })
            
            payment_method_datasets[payment_method][month_index] = amount
        
        # Format monthly totals (keeping existing structure for compatibility)
        for month in calendar.month_name[1:]:  # Skip empty first item
            monthly_totals.append({
                'month': month,
                'payment': monthly_data.get(month, [])
            })
        
        # Create datasets for charts
        labels = list(calendar.month_name)[1:]  # Skip empty first item
        datasets = []
        total_expenses_by_month = [0.0] * 12
        
        for payment_method, monthly_amounts in payment_method_datasets.items():
            if payment_method != 'Investimento':  # Exclude investments from totals
                datasets.append({
                    'label': payment_method,
                    'data': monthly_amounts
                })
                # Add to total expenses
                total_expenses_by_month = [sum(x) for x in zip(total_expenses_by_month, monthly_amounts)]
        
        # Process income data for combined datasets
        income_datasets = [0.0] * 12
        for item in income_by_month:
            month_index = item['month'].month - 1
            income_datasets[month_index] = float(item['total_amount'])
        
        # Create combined expense/income datasets
        combined_datasets = {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Total Expenses',
                    'datasets': total_expenses_by_month
                },
                {
                    'label': 'Total Income',
                    'datasets': income_datasets
                }
            ]
        }
        
        return {
            'monthly_totals': monthly_totals,
            'datasets': {
                'labels': labels,
                'datasets': datasets
            },
            'combined_datasets': combined_datasets
        }

    def get_optimized_monthly_expenses(self, month):
        """
        OPTIMIZED: Get monthly expenses with proper select_related to avoid N+1 queries.
        
        Performance: Eliminates N+1 queries by using select_related for foreign keys.
        """
        return self.expense_repository.get_optimized_monthly_expenses_with_relations(self.year, month)

    def _debug_category_calculation(self, payment_method, month: int, expenses: List[CategoryExpense]):
        """Debug logging for category calculations."""
        debug_to_json(
            data={
                'payment_method': payment_method.name,
                'month': calendar.month_name[month],
                'expenses': [
                    {
                        'category': expense.name,
                        'amount': float(expense.amount),
                        'month': expense.month
                    }
                    for expense in expenses
                ]
            },
            filename_prefix=f'category_calculation_{payment_method.name.replace("/", "_")}'
        )

    def _debug_final_results(self, results: List[MonthlyExpenseReport]):
        """Debug logging for final formatted results."""
        debug_to_json(
            data=[
                {
                    'month': report.month,
                    'total': float(report.total),
                    'categories': report.categories
                }
                for report in results
            ],
            filename_prefix='monthly_category_expenses'
        )
