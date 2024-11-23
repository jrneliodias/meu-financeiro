import json
from datetime import datetime
from itertools import groupby
from operator import itemgetter
from reports.repository import ExpenseRepository, PaymentMethodRepository
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime
from datetime import date
from registers.models import Expense, PaymentMethod
from django.db.models import Sum
import json
import calendar
from decimal import Decimal
from .utils import convert_values_to_float


class ExpenseService:
    def __init__(self, expense_repository, income_repository, year):

        self.expense_repository = expense_repository
        self.income_repository = income_repository
        self.year = year

    def calculate_monthly_payment_method_total_expense(self, ):
        payment_methods = PaymentMethod.objects.all()
        labels = [month for month in calendar.month_name if month]
        datasets = []
        for payment_method in payment_methods:
            monthly_expenses = {month: 0 for month in labels}
            day = payment_method.start_billing_day

            monthly_expenses = self.calculate_total_expense_for_payment_method(
                monthly_expenses, payment_method, day
            )

            datasets.append({
                "label": payment_method.name,
                "data": [monthly_expenses[month] for month in labels],
            })

        return {
            "labels": labels,
            "datasets": datasets,
        }

    def calculate_monthly_expenses_total(self):
        monthly_payment_method_expense_totals = self.calculate_monthly_payment_method_total_expense()
        datasets = monthly_payment_method_expense_totals["datasets"]

        total_sum = [0]*len(datasets[0]["data"])

        for dataset in datasets:
            if dataset['label'] != 'Investimento':
                total_sum = [sum(x) for x in zip(total_sum, dataset["data"])]

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
        return (
            self.expense_repository
            .get_total_payment_method_expenses_by_filter(
                payment_method, start_date, end_date
            )
        ) or Decimal('0')

    def get_billing_month(self, day, start_date, end_date):
        return (
            start_date.strftime("%B")
            if day == 1 else
            end_date.strftime("%B")
        )

    def calculate_total_expense_for_payment_method(self, expenses_by_month, payment_method, day):
        for month in range(1, 13):
            start_date = date(self.year, month, day)
            if month == 12:
                end_date = date(self.year, 12, calendar.monthrange(
                    self.year, 12)[1])  # Last day of December
            else:
                end_date = date(self.year, month + 1, day)
            total_expenses = self.get_total_expenses_amount_by_payment_method(
                payment_method, start_date, end_date)

            billing_month = self.get_billing_month(day, start_date, end_date)
            expenses_by_month[billing_month] += total_expenses
        monthy_payment_method_expense_float = convert_values_to_float(
            expenses_by_month)
        return monthy_payment_method_expense_float

    def calculate_time_interval_for_custom_start_billing_day(self, month_list: list[tuple[str, str]], year: int):
        payment_methods = PaymentMethodRepository.get_start_billing_days_payment_methods()
        interval_filter = []
        for payment_method in payment_methods:
            if (payment_method['start_billing_day'] == 1):
                continue
            for month_num, month_name in month_list:
                previous_month = int(month_num) - \
                    1 if int(month_num) > 1 else 12
                current_month_start = datetime(
                    year, previous_month, payment_method['start_billing_day'])
                current_month_end = datetime(
                    year, month_num, payment_method['start_billing_day'])
                interval_filter.append(
                    (month_name, current_month_start, current_month_end))
        return interval_filter

    def get_total_expenses_amount_by_payment_method_and_month(self, month_list: list[tuple[str, str]], year: int):

        interval_filter = self.calculate_time_interval_for_custom_start_billing_day(
            month_list, year)

        for interval in interval_filter:
            previous_month_24th = interval[1]
            current_month_24th = interval[2]
            credit_expenses = ExpenseRepository.get_expenses_by_filter({
                'start_date': previous_month_24th,
                'end_date': current_month_24th,
                'values': 'category__name'
            })
            expense_by_category = {}
            for credit_expense in credit_expenses:
                category = credit_expense['category__name']
                total_amount = credit_expense['total_amount']
                if category in expense_by_category:
                    expense_by_category[category] += total_amount
                else:
                    expense_by_category[category] = total_amount

    def monthly_payment_method_expense_totals(self, year: int):
        payments_data = self.expense_repository.get_total_expenses_amount_by_payment_method_and_month(
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

        # with open('expenses_by_payment.json', 'w', encoding='utf-8') as file:
        #     json.dump(transformed_payments, file,
        #               ensure_ascii=False, indent=4, cls=DjangoJSONEncoder)

        return transformed_payments
