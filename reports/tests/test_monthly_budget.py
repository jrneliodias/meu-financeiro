from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, CategoryBudgetEstimate, Expense, Installment, PaymentMethod, RecurringExpense
from reports.services.budget import monthly_budget


class MonthlyBudgetExpectedTotalTest(TestCase):
    """Expected total of a bill = fixed (active recurring) + the bill's installments + category estimates."""

    def test_expected_sums_fixed_installments_and_estimates(self):
        user = User.objects.create_user(username='test')
        food = Category.objects.create(name='Food', type='expense')
        card = PaymentMethod.objects.create(name='Card', start_billing_day=1)
        RecurringExpense.objects.create(user=user, description='Rent', total_amount=Decimal('500.00'),
                                        start_date=date(2026, 1, 5), category=food, payment_method=card)
        # 300 in June, 300 in July
        Installment.create_plan(user, description='TV', total_amount=Decimal('600.00'), total_installments=2,
                                start_date=date(2026, 6, 10), category=food, payment_method=card)
        CategoryBudgetEstimate.objects.create(user=user, category=food, amount=Decimal('150.00'), month=6, year=2026)
        # 500 (fixed) + 300 (installments) + 150 (estimated) = 950
        self.assertEqual(monthly_budget(user, month=6, year=2026).total_expected, Decimal('950.00'))


class MonthlyBudgetRulesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='planner')
        self.food = Category.objects.create(name='Food', type='expense')
        self.card = PaymentMethod.objects.create(name='Card', start_billing_day=3)

    def spend(self, amount, day, category=None, **links):
        return Expense.objects.create(user=self.user, description='x', amount=Decimal(amount), date=day,
                                      category=category or self.food, payment_method=self.card, **links)

    def recurring(self, amount='50', start=date(2026, 1, 10), **fields):
        return RecurringExpense.objects.create(user=self.user, description='Gym', total_amount=Decimal(amount),
                                               start_date=start, category=self.food, payment_method=self.card,
                                               **fields)

    def estimate(self, amount):
        CategoryBudgetEstimate.objects.create(user=self.user, category=self.food, amount=Decimal(amount),
                                              month=5, year=2026)

    def test_regular_total_excludes_recurring_and_installment_expenses(self):
        self.spend('40', date(2026, 5, 10))
        Installment.create_plan(self.user, description='TV', total_amount=Decimal('100'), total_installments=1,
                                start_date=date(2026, 5, 11), category=self.food, payment_method=self.card)
        self.spend('50', date(2026, 5, 12), reccurring_expense=self.recurring())
        self.assertEqual(monthly_budget(self.user, 2026, 5).total_regular, Decimal('40'))

    def test_totals_follow_the_bill_not_the_calendar(self):
        self.spend('40', date(2026, 6, 2))  # before the 3rd: May's bill
        self.assertEqual(monthly_budget(self.user, 2026, 5).total_regular, Decimal('40'))
        self.assertEqual(monthly_budget(self.user, 2026, 6).total_regular, Decimal('0'))

    def test_category_actual_and_over_budget_flag(self):
        self.estimate('100')
        self.spend('150', date(2026, 5, 10))
        item = monthly_budget(self.user, 2026, 5).estimates[0]
        self.assertEqual((item.actual_amount, item.progress_percentage, item.is_over_budget),
                         (Decimal('150'), 150.0, True))

    def test_progress_is_capped_at_999(self):
        self.estimate('1')
        self.spend('50', date(2026, 5, 10))
        self.assertEqual(monthly_budget(self.user, 2026, 5).estimates[0].progress_percentage, 999.0)

    def test_zero_estimate_does_not_divide_by_zero(self):
        # whether spending against a R$ 0 estimate is "over budget" is an open decision
        self.estimate('0')
        self.spend('50', date(2026, 5, 10))
        self.assertEqual(monthly_budget(self.user, 2026, 5).estimates[0].progress_percentage, 0.0)

    def test_fixed_total_counts_only_schedules_due_that_month_with_iof(self):
        self.recurring('100', start=date(2026, 5, 10), is_international=True)
        self.recurring('70', generate_debit=False)
        self.assertEqual(monthly_budget(self.user, 2026, 4).total_fixed, Decimal('0'))
        self.assertEqual(monthly_budget(self.user, 2026, 5).total_fixed, Decimal('103.50'))

    def test_adjusted_expected_adds_spending_outside_the_plan(self):
        self.recurring('50')
        self.estimate('100')
        self.spend('40', date(2026, 5, 10), category=Category.objects.create(name='Fun', type='expense'))
        budget = monthly_budget(self.user, 2026, 5)
        self.assertEqual(budget.total_expected, Decimal('150'))
        self.assertEqual(budget.adjusted_expected, Decimal('190'))
