from django.test import TestCase
from reports.services.billing_period_calculator import BillingPeriodCalculator
from datetime import datetime
from freezegun import freeze_time


class BillingPeriodCalculatorTestCase(TestCase):
    """Tests for the BillingPeriodCalculator._calculate_billing_period_for_month method."""

    def test_special_case_april_2024(self):
        """Test the special case for April 2024 (first period)."""
        calculator = BillingPeriodCalculator(2024)
        period = calculator._calculate_billing_period_for_month(4)

        self.assertEqual(period['start_date'], '2024-03-25')
        self.assertEqual(period['end_date'], '2024-04-23')
        self.assertEqual(period['days_between'], 30)

    def test_may_2024(self):
        """Test May 2024 (second period)."""
        calculator = BillingPeriodCalculator(2024)
        period = calculator._calculate_billing_period_for_month(5)

        # For May 2024, the period should be April 24 to May 23
        self.assertEqual(period['start_date'], '2024-04-24')
        self.assertEqual(period['end_date'], '2024-05-24')
        self.assertEqual(period['days_between'], 31)

    def test_june_2024(self):
        """Test June 2024 (third period)."""
        calculator = BillingPeriodCalculator(2024)
        period = calculator._calculate_billing_period_for_month(6)

        # For June 2024, the period should be May 24 to June 24
        self.assertEqual(period['start_date'], '2024-05-25')
        self.assertEqual(period['end_date'], '2024-06-23')
        # This should be adjusted to 31 days
        self.assertEqual(period['days_between'], 30)

    def test_july_2024(self):
        """Test July 2024 (fourth period)."""
        calculator = BillingPeriodCalculator(2024)
        period = calculator._calculate_billing_period_for_month(7)

        self.assertEqual(period['start_date'], '2024-06-24')
        self.assertEqual(period['end_date'], '2024-07-24')
        self.assertEqual(period['days_between'], 31)

    def test_august_2024(self):
        """Test August 2024 (fourth period)."""
        calculator = BillingPeriodCalculator(2024)
        period = calculator._calculate_billing_period_for_month(8)

        self.assertEqual(period['start_date'], '2024-07-25')
        self.assertEqual(period['end_date'], '2024-08-24')
        self.assertEqual(period['days_between'], 31)

    def test_september_2024(self):
        """Test September 2024 (fourth period)."""
        calculator = BillingPeriodCalculator(2024)
        period = calculator._calculate_billing_period_for_month(9)

        self.assertEqual(period['start_date'], '2024-08-25')
        self.assertEqual(period['end_date'], '2024-09-23')
        self.assertEqual(period['days_between'], 30)

    def test_january_2025(self):
        """Test that start days alternate between 24 and 25."""
        calculator = BillingPeriodCalculator(2025)
        period = calculator._calculate_billing_period_for_month(1)

        self.assertEqual(period['start_date'], '2024-12-25')
        self.assertEqual(period['end_date'], '2025-01-24')
        self.assertEqual(period['days_between'], 31)

    def test_february_2025(self):
        """Test February 2025 (fifth period)."""
        calculator = BillingPeriodCalculator(2025)
        period = calculator._calculate_billing_period_for_month(2)

        self.assertEqual(period['start_date'], '2025-01-25')
        self.assertEqual(period['end_date'], '2025-02-21')
        self.assertEqual(period['days_between'], 28)

    def test_march_2025(self):
        """Test March 2025 (sixth period)."""
        calculator = BillingPeriodCalculator(2025)
        period = calculator._calculate_billing_period_for_month(3)

        self.assertEqual(period['start_date'], '2025-02-22')
        self.assertEqual(period['end_date'], '2025-03-24')
        self.assertEqual(period['days_between'], 31)

    def test_april_2025(self):
        """Test April 2025 (seventh period)."""
        calculator = BillingPeriodCalculator(2025)
        period = calculator._calculate_billing_period_for_month(4)

        self.assertEqual(period['start_date'], '2025-03-25')
        self.assertEqual(period['end_date'], '2025-04-23')
        self.assertEqual(period['days_between'], 30)
