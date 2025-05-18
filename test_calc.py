#!/usr/bin/env python
from datetime import datetime
import calendar


class BillingPeriodCalculator:
    def __init__(self, year: int):
        self.year = year

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


def print_billing_periods_for_year(year):
    """Print all billing periods for a given year."""
    calculator = BillingPeriodCalculator(year)

    print(f"Billing periods for {year}:")
    print("=" * 50)

    for month in range(1, 13):
        period = calculator._calculate_billing_period_for_month(month)
        month_name = datetime(year, month, 1).strftime("%B")

        print(f"{month_name}:")
        print(f"  Start: {period['start_date']}")
        print(f"  End:   {period['end_date']}")
        print(f"  Days:  {period['days_between']}")
        print()


def test_specific_periods():
    """Test specific billing periods against expected values."""
    # Test cases from the provided data
    test_cases = [
        # month, year, expected_start, expected_end, expected_days
        (2, 2024, "2024-01-25", "2024-02-22", 29),
        (3, 2024, "2024-02-23", "2024-03-24", 31),
        (4, 2024, "2024-03-25", "2024-04-23", 30),
        (5, 2024, "2024-04-24", "2024-05-24", 31),
        (6, 2024, "2024-05-25", "2024-06-23", 30),
        (7, 2024, "2024-06-24", "2024-07-24", 31),
        (8, 2024, "2024-07-25", "2024-08-24", 31),
        (9, 2024, "2024-08-25", "2024-09-23", 30),
        (10, 2024, "2024-09-24", "2024-10-24", 31),
        (11, 2024, "2024-10-25", "2024-11-23", 30),
        (12, 2024, "2024-11-24", "2024-12-24", 31),
        (1, 2025, "2024-12-25", "2025-01-24", 31),
        (2, 2025, "2025-01-25", "2025-02-21", 28),
        (3, 2025, "2025-02-22", "2025-03-24", 31),
        (4, 2025, "2025-03-25", "2025-04-23", 30),
    ]

    print("Testing specific billing periods:")
    print("=" * 50)

    all_passed = True

    for month, year, expected_start, expected_end, expected_days in test_cases:
        calculator = BillingPeriodCalculator(year)
        period = calculator._calculate_billing_period_for_month(month)

        month_name = datetime(year, month, 1).strftime("%B")
        actual_start = period['start_date']
        actual_end = period['end_date']
        actual_days = period['days_between']

        success = (
            actual_start == expected_start and
            actual_end == expected_end and
            actual_days == expected_days
        )

        result = "PASS" if success else "FAIL"
        print(f"{month_name} {year}: {result}")

        if not success:
            print(
                f"  Expected: {expected_start} to {expected_end} ({expected_days} days)")
            print(
                f"  Actual:   {actual_start} to {actual_end} ({actual_days} days)")
            all_passed = False

        if not success:
            print()

    if all_passed:
        print("\nAll test cases passed successfully!")
    else:
        print("\nSome test cases failed. Please check the implementation.")


if __name__ == "__main__":
    # Print all billing periods for 2024 (leap year)
    print_billing_periods_for_year(2024)
    print()

    # Print all billing periods for 2025 (non-leap year)
    print_billing_periods_for_year(2025)
    print()

    # Test specific periods against expected values
    test_specific_periods()
