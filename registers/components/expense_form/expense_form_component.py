from datetime import date
from django import forms
from .base_form_component import BaseFormComponent
from .quick_fill_menu import QuickFillMenu
from registers.models import Category, PaymentMethod


class ExpenseFormComponent(BaseFormComponent):
    """Expense form component implementing Interface Segregation"""

    def __init__(self, user, quick_fill_menu: QuickFillMenu):
        self.user = user
        self.quick_fill_menu = quick_fill_menu

    def get_initial_data(self):
        """Get initial form data"""
        return {
            'date': date.today(),
            'installments': 1,
        }

    def get_form_fields(self):
        """Get form fields configuration"""
        return {
            'description': forms.CharField(max_length=200),
            'amount': forms.DecimalField(max_digits=10, decimal_places=2),
            'installments': forms.IntegerField(min_value=1, initial=1),
            'date': forms.DateField(widget=forms.DateInput(attrs={'type': 'date'})),
            'category': forms.ModelChoiceField(
                queryset=Category.objects
            ),
            'payment_method': forms.ModelChoiceField(
                queryset=PaymentMethod.objects
            ),
        }

    def apply_quick_fill(self, option_key: str, form):
        """Apply quick fill option to form"""
        option = self.quick_fill_menu.get_option(option_key)
        if option:
            form.initial['description'] = option.description
            if option.default_amount:
                form.initial['amount'] = option.default_amount

            try:
                category = Category.objects.get(
                    name=option.category_name
                )
                form.initial['category'] = category.id
            except Category.DoesNotExist:
                pass

            try:
                payment_method = PaymentMethod.objects.get(
                    name=option.payment_method_name
                )
                form.initial['payment_method'] = payment_method.id
            except PaymentMethod.DoesNotExist:
                pass
