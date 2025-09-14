#!/usr/bin/env python
from datetime import datetime
import calendar
from reports.services.billing_period_calculator import BillingPeriodCalculator


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

        # Calculate expected days (just for verification)
        start_date = datetime.strptime(period['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(period['end_date'], "%Y-%m-%d")
        actual_days = (end_date - start_date).days + 1

        if actual_days != period['days_between']:
            print(
                f"  WARNING: Day count mismatch! Calculated: {period['days_between']}, Actual: {actual_days}")

     


if __name__ == "__main__":
    # Test for 2024 (leap year)
    print_billing_periods_for_year(2024)

    # Test for 2025 (non-leap year)
    print_billing_periods_for_year(2025)
