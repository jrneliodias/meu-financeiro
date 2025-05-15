from datetime import date
import calendar
from reports.dataclasses import BillingPeriod
from datetime import datetime, timedelta
from calendar import monthrange


class BillingPeriodCalculator:
    # Billing period configuration - maps month number to (start_day, end_day, expected_days)
    # For months with variable days (Feb, Mar), these are base values before leap year adjustments
    BILLING_PERIODS = {
        1: (25, 24, 31),  # January: Dec 25 - Jan 24, 31 days
        2: (25, 21, 28),  # February: Jan 25 - Feb 21, 28 days (non-leap)
        3: (22, 24, 31),  # March: Feb 22 - Mar 24, 31 days
        4: (25, 23, 30),  # April: Mar 25 - Apr 23, 30 days
        5: (24, 24, 31),  # May: Apr 24 - May 24, 31 days
        6: (25, 23, 30),  # June: May 25 - Jun 23, 30 days
        7: (24, 24, 31),  # July: Jun 24 - Jul 24, 31 days
        8: (25, 24, 31),  # August: Jul 25 - Aug 24, 31 days
        9: (25, 23, 30),  # September: Aug 25 - Sep 23, 30 days
        10: (24, 24, 31),  # October: Sep 24 - Oct 24, 31 days
        11: (25, 23, 30),  # November: Oct 25 - Nov 23, 30 days
        12: (24, 24, 31),  # December: Nov 24 - Dec 24, 31 days
    }

    def __init__(self, year: int):
        self.year = year

    def calculate_period(self, month: int, billing_day: int) -> BillingPeriod:
        """Calculate billing period for a given month and billing day."""
        if billing_day == 1:
            return self._calculate_calendar_month_period(month)
        return self._calculate_billing_period_for_month(month)

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

    def _get_previous_month_and_year(self, month: int) -> tuple:
        """Calculate the previous month and year for a given month."""
        if month == 1:
            return 12, self.year - 1
        return month - 1, self.year

    def _adjust_for_leap_year(self, month: int, start_day: int, end_day: int) -> tuple:
        """Adjust start and end days for leap years."""
        is_leap_year = calendar.isleap(self.year)

        # February's end day is 22 in leap years, 21 otherwise
        if month == 2 and is_leap_year:
            end_day = 22

        # March's start day is 23 in leap years, 22 otherwise
        if month == 3:
            prev_year = self.year
            if month == 3 and month - 1 == 2:  # Previous month is February
                # Check if previous February was in a leap year
                is_prev_leap_year = calendar.isleap(prev_year)
                if is_prev_leap_year:
                    start_day = 23

        return start_day, end_day

    def _ensure_correct_period_length(self, start_date: datetime, end_date: datetime, expected_days: int) -> datetime:
        """Ensure the billing period has the correct number of days."""
        actual_days = (end_date - start_date).days + 1

        if actual_days != expected_days:
            # Adjust end date to match expected days
            end_date = start_date + timedelta(days=expected_days - 1)

        return end_date

    def _calculate_billing_period_for_month(self, month: int):
        """
        Calculate Nubank credit card billing period for a given month.

        The method uses a configuration table to determine start day, end day, 
        and expected days for each month, with adjustments for leap years.

        Args:
            month (int): The billing month (1-12)

        Returns:
            dict: {
                'start_date': 'YYYY-MM-DD',
                'end_date': 'YYYY-MM-DD',
                'days_between': int
            }
        """
        # Validate month input
        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12")

        # Get configuration for this month
        start_day, end_day, expected_days = self.BILLING_PERIODS[month]

        # Calculate previous month and year for start date
        prev_month, prev_year = self._get_previous_month_and_year(month)

        # Adjust for leap years
        start_day, end_day = self._adjust_for_leap_year(
            month, start_day, end_day)

        # Adjust expected days for February in leap years
        if month == 2 and calendar.isleap(self.year):
            expected_days = 29

        # Create date objects
        start_date = datetime(prev_year, prev_month, start_day)
        end_date = datetime(self.year, month, end_day)

        # Ensure correct period length
        end_date = self._ensure_correct_period_length(
            start_date, end_date, expected_days)

        # The billing month is the month containing the end date
        billing_month = end_date.strftime('%B')

        return BillingPeriod(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), billing_month)
