from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Case, F, Q, When
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils.translation import gettext_lazy as _

from utils.dates import month_end


class CategoryQuerySet(models.QuerySet):
    def expense(self):
        return self.filter(type='expense')

    def income(self):
        return self.filter(type='income')


class Category(models.Model):
    name = models.CharField(max_length=100)
    CATEGORY_TYPES = [
        ('income', _('Income')),
        ('expense', _('Expense')),
    ]
    type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CategoryQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    start_billing_day = models.IntegerField(
        help_text=_("Day of the month when billing starts"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Installment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_installments = models.IntegerField()
    start_date = models.DateField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, limit_choices_to={'type': 'expense'})
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - Total: {self.total_amount} ({self.total_installments} installments)"

    @classmethod
    def create_plan(cls, user, *, description, total_amount, total_installments,
                    start_date, category, payment_method):
        """The plan plus one expense per month, each `total / n`, described "desc - i/n"."""
        plan = cls.objects.create(
            user=user, description=description, total_amount=total_amount,
            total_installments=total_installments, start_date=start_date,
            category=category, payment_method=payment_method,
        )
        for i in range(total_installments):
            Expense.objects.create(
                user=user, description=f"{description} - {i + 1}/{total_installments}",
                amount=total_amount / total_installments,
                date=start_date + relativedelta(months=i),
                category=category, payment_method=payment_method, installment_plan=plan,
            )
        return plan


class RecurringExpenseQuerySet(models.QuerySet):
    def due_in(self, year, month):
        """Active schedules that have started by the end of month/year: the ones that get an expense that month."""
        return self.filter(generate_debit=True, start_date__lte=month_end(year, month))

    def charged_total(self):
        """What these schedules add to a bill, IOF included."""
        return sum((recurring.charged_amount for recurring in self), Decimal('0'))


class RecurringExpense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, limit_choices_to={'type': 'expense'})
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.SET_NULL, null=True)
    generate_debit = models.BooleanField(default=True)
    is_international = models.BooleanField(
        default=False, help_text=_("Charged in foreign currency: IOF is added to the generated expense"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # IOF on international credit card purchases (3.5% since 2025)
    IOF_RATE = Decimal('0.035')

    objects = RecurringExpenseQuerySet.as_manager()

    @property
    def charged_amount(self):
        """Amount that lands on the bill: total_amount (BRL, before IOF) + IOF if international."""
        if self.is_international:
            return (self.total_amount * (1 + self.IOF_RATE)).quantize(Decimal('0.01'))
        return self.total_amount

    def __str__(self):
        return f"{self.description}"

    def due_date(self, year, month):
        """Same day as start_date, clamped to the month's last day (31 → Feb 28)."""
        return date(year, month, min(self.start_date.day, month_end(year, month).day))

    def month_expense(self, year, month):
        """The expense generated for this calendar month (at most one), or None."""
        return self.recurring_expenses.in_month(year, month).first()

    def generate_for_month(self, year, month):
        """Create this month's unpaid expense unless it exists. Returns (expense, created)."""
        existing = self.month_expense(year, month)
        if existing:
            return existing, False
        return Expense.objects.create(
            user=self.user, reccurring_expense=self, is_paid=False, **self._occurrence_fields(year, month),
        ), True

    def sync_month_expense(self, year, month):
        """Copy this schedule onto the month's expense (paid status untouched); None if missing."""
        expense = self.month_expense(year, month)
        if expense is None:
            return None
        for field, value in self._occurrence_fields(year, month).items():
            setattr(expense, field, value)
        expense.save()
        return expense

    @classmethod
    def start_from(cls, expense):
        """A monthly schedule repeating `expense` from its date on (the inverse of _occurrence_fields)."""
        return cls.objects.create(
            user=expense.user, description=expense.description, total_amount=expense.amount,
            start_date=expense.date, category=expense.category, payment_method=expense.payment_method,
        )

    def _occurrence_fields(self, year, month):
        """What the month's expense copies from this schedule."""
        return {
            'description': self.description, 'amount': self.charged_amount, 'date': self.due_date(year, month),
            'category': self.category, 'payment_method': self.payment_method,
        }


def _first_of_month(year, month, months_ahead=0):
    years, month_index = divmod(month - 1 + months_ahead, 12)
    return date(year + years, month_index + 1, 1)


class ExpenseQuerySet(models.QuerySet):
    def with_billing_month(self):
        """Annotate billing_year/billing_month: an expense dated before its payment method's
        start_billing_day belongs to the previous month's bill (start day 3 → Oct 3..Nov 2 is October)."""
        before_start = Q(date__day__lt=F('payment_method__start_billing_day'))
        return self.annotate(
            billing_month=Case(
                When(before_start & Q(date__month=1), then=12),
                When(before_start, then=ExtractMonth('date') - 1),
                default=ExtractMonth('date'),
            ),
            billing_year=Case(
                When(before_start & Q(date__month=1), then=ExtractYear('date') - 1),
                default=ExtractYear('date'),
            ),
        )

    def in_billing_month(self, year, month):
        # The bill of month M only holds expenses dated in M or M+1.
        return (self.filter(date__gte=_first_of_month(year, month),
                            date__lt=_first_of_month(year, month, 2))
                .with_billing_month().filter(billing_year=year, billing_month=month))

    def in_billing_year(self, year):
        # A billing year spills into early next year (Jan 1-2 → December bill).
        return (self.filter(date__gte=date(year, 1, 1), date__lt=date(year + 1, 2, 1))
                .with_billing_month().filter(billing_year=year))

    def in_month(self, year, month):
        """Calendar month, for lists ordered by the day the expense happened."""
        return self.filter(date__year=year, date__month=month)


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    date = models.DateField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, limit_choices_to={'type': 'expense'})
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    installment_plan = models.ForeignKey(
        Installment, on_delete=models.CASCADE, null=True, blank=True, related_name='expenses')
    reccurring_expense = models.ForeignKey(
        RecurringExpense, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_expenses')
    is_paid = models.BooleanField(default=True)
    paid_at = models.DateField(null=True, blank=True)

    objects = ExpenseQuerySet.as_manager()

    def __str__(self):
        return f"{self.description} - {self.category} - {str(self.amount)}"

    KIND_LABELS = {'installment': _('Installment'), 'recurring': _('Recurring'), 'single': _('Single')}

    @property
    def kind(self):
        """'installment', 'recurring' or 'single'; an installment wins over a recurring link."""
        if self.installment_plan_id:
            return 'installment'
        if self.reccurring_expense_id:
            return 'recurring'
        return 'single'

    @property
    def kind_label(self):
        return self.KIND_LABELS[self.kind]


class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    date = models.DateField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, limit_choices_to={'type': 'income'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - {str(self.amount)}"


class QuickFillPreset(models.Model):
    """Pre-configured expense templates for rapid data entry via quick fill buttons."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    default_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'type': 'expense'}
    )
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True
    )
    icon = models.CharField(max_length=50, default='fa-bolt')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = _('Quick Fill Preset')
        verbose_name_plural = _('Quick Fill Presets')

    def __str__(self):
        return self.name


class Investment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    investment_type = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.description} - {str(self.amount)}"


class CategoryBudgetEstimate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budget_estimates')
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE,
        limit_choices_to={'type': 'expense'}
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.IntegerField()
    year = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'category', 'month', 'year')]
        ordering = ['category__name']

    def __str__(self):
        return f"{self.category.name} - {self.month}/{self.year}: R${self.amount}"
