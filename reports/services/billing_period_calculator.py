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

        Args:
            month (int): The billing month (1-12)

        Returns:
            dict: {
                'start_date': 'YYYY-MM-DD',
                'end_date': 'YYYY-MM-DD',
                'days_between': int
            }
        """
        # Calculate previous year for January billing period
        if month == 1:
            prev_year = self.year - 1
        else:
            prev_year = self.year

        # Check if it's a leap year
        is_leap_year = calendar.isleap(self.year)

        # Dictionary mapping months to (start_date, end_date) datetime tuples
        # Using datetime objects allows for easier manipulation and dates beyond day 31
        billing_periods = {
            # January: Dec 25 to Jan 24
            1: (datetime(prev_year, 12, 25), datetime(self.year, 1, 24)),
            # February: Jan 25 to Feb 22/21 (leap year handling)
            2: (datetime(self.year, 1, 25), datetime(self.year, 2, 22 if is_leap_year else 21)),
            # March: Feb 23/22 to Mar 24
            3: (datetime(self.year, 2, 23 if is_leap_year else 22), datetime(self.year, 3, 24)),
            # April: Mar 25 to Apr 23
            4: (datetime(self.year, 3, 25), datetime(self.year, 4, 23)),
            # May: Apr 24 to May 24
            5: (datetime(self.year, 4, 24), datetime(self.year, 5, 24)),
            # June: May 25 to Jun 23
            6: (datetime(self.year, 5, 25), datetime(self.year, 6, 23)),
            # July: Jun 24 to Jul 24
            7: (datetime(self.year, 6, 24), datetime(self.year, 7, 24)),
            # August: Jul 25 to Aug 24
            8: (datetime(self.year, 7, 25), datetime(self.year, 8, 24)),
            # September: Aug 25 to Sep 23
            9: (datetime(self.year, 8, 25), datetime(self.year, 9, 23)),
            # October: Sep 24 to Oct 24
            10: (datetime(self.year, 10, 4), datetime(self.year, 11, 3)),
            # November: Oct 25 to Nov 23
            11: (datetime(self.year, 11, 3), datetime(self.year, 12, 23)),
            # December: Nov 24 to Dec 24
            12: (datetime(self.year, 12, 4), datetime(self.year+1, 1, 3)),
        }

        # Get start and end dates from the dictionary
        start_date, end_date = billing_periods[month]

        # Calculate days between
        days_between = (end_date - start_date).days + 1

        return {
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'days_between': days_between
        }
