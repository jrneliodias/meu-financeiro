from datetime import datetime
from reports.repository.payment_method_repository import PaymentMethodRepository
from reports.repository.expense_repository import ExpenseRepository


def calculate_time_interval_for_custom_start_billing_day(month_list: list[tuple[str, str]], year: int):
    payment_methods = PaymentMethodRepository.get_start_billing_days_payment_methods()
    interval_filter = []
    for payment_method in payment_methods:
        if (payment_method['start_billing_day'] == 1):
            continue
        print(payment_method['name'])
        for month_num, month_name in month_list:
            previous_month = int(month_num) - 1 if int(month_num) > 1 else 12
            current_month_start = datetime(
                year, previous_month, payment_method['start_billing_day'])
            current_month_end = datetime(
                year, month_num, payment_method['start_billing_day'])
            interval_filter.append(
                (month_name, current_month_start, current_month_end))
    return interval_filter


def get_total_expenses_amount_by_payment_method_and_month(month_list: list[tuple[str, str]], year: int):

    interval_filter = calculate_time_interval_for_custom_start_billing_day(
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
