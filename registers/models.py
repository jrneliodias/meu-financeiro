from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Create your models here.


class Category(models.Model):
    name = models.CharField(max_length=100)
    CATEGORY_TYPES = [
        ('income', _('Income')),
        ('expense', _('Expense')),
    ]
    type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description}"


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

    def __str__(self):
        return f"{self.description} - {self.category} - {str(self.amount)}"


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
