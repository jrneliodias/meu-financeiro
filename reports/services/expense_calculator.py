from reports.dataclasses import BillingPeriod
from reports.services.billing_period_calculator import BillingPeriodCalculator
from datetime import date
import calendar
from typing import Dict
from reports.utils import debug_to_json


class ExpenseCalculator:
    def __init__(self, expense_repository, year: int):
        self.expense_repository = expense_repository
        self.billing_calculator = BillingPeriodCalculator(year)

    def calculate_monthly_expenses(self, payment_method, billing_day: int) -> Dict[str, float]:
        """Calculate monthly expenses for a payment method."""
        monthly_expenses = {month: 0 for month in calendar.month_name[1:]}

        for month in range(1, 13):
            period = self.billing_calculator.calculate_period(
                month, billing_day)

            total_expenses = self._get_period_expenses(
                payment_method,
                period.start_date,
                period.end_date
            )

            monthly_expenses[period.billing_month] += total_expenses

            self._debug_period_calculation(
                payment_method, period, total_expenses)

        return monthly_expenses

    def _get_period_expenses(self, payment_method, start_date: date, end_date: date) -> float:
        """Get total expenses for a period."""
        return float(
            self.expense_repository.get_total_payment_method_expenses_by_filter(
                payment_method, start_date, end_date
            ) or 0
        )

    def _debug_period_calculation(self, payment_method, period: BillingPeriod, total_expenses: float):
        """Log debug information for period calculation."""
        debug_to_json(
            data={
                'payment_method': payment_method.name,
                'period': {
                    'start_date': str(period.start_date),
                    'end_date': str(period.end_date),
                    'billing_month': period.billing_month,
                },
                'total_expenses': total_expenses
            },
            filename_prefix=f'period_calculation_{payment_method.name.replace("/", "_")}'
        )
