from datetime import date
import calendar
from reports.dataclasses import BillingPeriod


class BillingPeriodCalculator:
    def __init__(self, year: int):
        self.year = year

    def calculate_period(self, month: int, billing_day: int) -> BillingPeriod:
        """Calculate billing period for a given month and billing day."""
        if billing_day == 1:
            return self._calculate_calendar_month_period(month)
        return self._calculate_custom_billing_period(month, billing_day)

    def _calculate_calendar_month_period(self, month: int) -> BillingPeriod:
        """Calculate period for billing_day = 1 (calendar month)."""
        start_date = date(self.year, month, 1)
        last_day = calendar.monthrange(self.year, month)[1]
        end_date = date(self.year, month, last_day)
        billing_month = start_date.strftime('%B')

        return BillingPeriod(start_date, end_date, billing_month)

    def _calculate_custom_billing_period(self, month: int, billing_day: int) -> BillingPeriod:
        """Calculate period for custom billing day."""
        # For month M, the period is from M-1/billing_day to M/billing_day-1
        # The expenses are attributed to month M

        # Calculate end date first (this determines the billing month)
        if month == 12:
            end_date = date(self.year, 12, billing_day - 1)
        else:
            end_date = date(self.year, month, billing_day - 1)

        # Calculate start date
        if month == 1:
            start_date = date(self.year - 1, 12, billing_day)
        else:
            start_date = date(self.year, month - 1, billing_day)

        # The billing month is the month containing the end date
        billing_month = end_date.strftime('%B')

        return BillingPeriod(start_date, end_date, billing_month)
