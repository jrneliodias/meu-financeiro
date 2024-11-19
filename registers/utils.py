from datetime import date, timedelta
from registers.models import Expense, PaymentMethod
from django.db.models import Sum
import json
import calendar


def calculate_total_expense_by_month():
    payment_methods = PaymentMethod.objects.all()
    labels = [month for month in calendar.month_name if month]
    datasets = []
    for payment_method in payment_methods:
        print(f"Payment method: {payment_method.name}")
        monthly_expenses = {month: 0 for month in labels}
        day = payment_method.start_billing_day

        monthly_expenses = calculate_total_expense_for_payment_method(
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


def get_total_expenses_amount_by_payment_method(payment_method, start_date, end_date):
    return (
        Expense.objects.filter(
            payment_method=payment_method,
            date__gte=start_date,
            date__lte=end_date
        )
        .aggregate(total=Sum('amount'))['total']
    ) or 0


def get_billing_month(day, start_date, end_date):
    return (
        start_date.strftime("%B")
        if day == 1 else
        end_date.strftime("%B")
    )


def calculate_total_expense_for_payment_method(expenses_by_month, payment_method, day):
    for month in range(5, 12):
        start_date = date(2024, month, day)
        end_date = date(2024, month+1, day)

        total_expenses = get_total_expenses_amount_by_payment_method(
            payment_method, start_date, end_date)

        billing_month = get_billing_month(day, start_date, end_date)
        print(
            f"{billing_month}: {total_expenses}")
        expenses_by_month[billing_month] += float(
            total_expenses)

    return expenses_by_month
