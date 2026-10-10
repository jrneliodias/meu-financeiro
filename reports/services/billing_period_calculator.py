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
        """Bill of month M runs from M/billing_day to (M+1)/(billing_day-1).

        Example: billing_day=3 → October bill is Oct 3 .. Nov 2.
        """
        start_date = self._period_start(self.year, month, billing_day)
        next_year, next_month = (self.year + 1, 1) if month == 12 else (self.year, month + 1)
        end_date = self._period_start(next_year, next_month, billing_day) - timedelta(days=1)
        billing_month = date(self.year, month, 1).strftime('%B')

        return BillingPeriod(start_date, end_date, billing_month)

    @staticmethod
    def _period_start(year: int, month: int, billing_day: int) -> date:
        # ponytail: billing_day past month end (e.g. 30 in Feb) starts on the 1st of the next
        # month, matching expense_repository.with_billing_month (day < billing_day → previous bill).
        if billing_day <= monthrange(year, month)[1]:
            return date(year, month, billing_day)
        return date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

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
