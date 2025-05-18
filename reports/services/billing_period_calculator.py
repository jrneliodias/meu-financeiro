from datetime import date
import calendar
from reports.dataclasses import BillingPeriod
from datetime import datetime, timedelta
from calendar import monthrange


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

    def _calculate_billing_period_for_month(self, month: int):
        """
        Calculate Nubank credit card billing period for a given month.

        The pattern is as follows:
        - January: Dec 25 to Jan 24
        - February: Jan 25 to Feb 22 (leap year) or Feb 21 (non-leap year)
        - March: Feb 23 (leap year) or Feb 22 (non-leap year) to Mar 24
        - April: Mar 25 to Apr 23
        - May: Apr 24 to May 24
        - June: May 25 to Jun 23
        - July: Jun 24 to Jul 24
        - August: Jul 25 to Aug 24
        - September: Aug 25 to Sep 23
        - October: Sep 24 to Oct 24
        - November: Oct 25 to Nov 23
        - December: Nov 24 to Dec 24

        Args:
            month (int): The billing month (1-12)

        Returns:
            dict: {
                'start_date': 'YYYY-MM-DD',
                'end_date': 'YYYY-MM-DD',
                'days_between': int
            }
        """
        # Calculate previous month and year
        if month == 1:
            prev_month = 12
            prev_year = self.year - 1
        else:
            prev_month = month - 1
            prev_year = self.year

        # Check if it's a leap year
        is_leap_year = calendar.isleap(self.year)

        # Dictionary mapping months to (start_day, end_day) tuples
        # For February and March, we use functions to handle leap year logic
        billing_periods = {
            1: (25, 24),  # January: Dec 25 to Jan 24
            # February: Jan 25 to Feb 22/21
            2: (25, 22 if is_leap_year else 21),
            3: (23 if is_leap_year else 22, 24),  # March: Feb 23/22 to Mar 24
            4: (25, 23),  # April: Mar 25 to Apr 23
            5: (24, 24),  # May: Apr 24 to May 24
            6: (25, 23),  # June: May 25 to Jun 23
            7: (24, 24),  # July: Jun 24 to Jul 24
            8: (25, 24),  # August: Jul 25 to Aug 24
            9: (25, 23),  # September: Aug 25 to Sep 23
            10: (24, 24),  # October: Sep 24 to Oct 24
            11: (25, 23),  # November: Oct 25 to Nov 23
            12: (24, 24),  # December: Nov 24 to Dec 24
        }

        # Get start and end days from the dictionary
        start_day, end_day = billing_periods[month]

        # Create date objects
        start_date = datetime(prev_year, prev_month, start_day)
        end_date = datetime(self.year, month, end_day)

        # Calculate days between
        days_between = (end_date - start_date).days + 1

        return {
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'days_between': days_between
        }
