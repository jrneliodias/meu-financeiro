from datetime import date
from django import forms
from django.utils.translation import gettext_lazy as _
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
            'description': forms.CharField(label=_('Description'), max_length=200),
            'amount': forms.DecimalField(label=_('Amount'), max_digits=10, decimal_places=2),
            'installments': forms.IntegerField(label=_('Installments'), min_value=1, initial=1),
            'date': forms.DateField(label=_('Date'), widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')),
            'category': forms.ModelChoiceField(
                label=_('Category'),
                queryset=Category.objects
            ),
            'payment_method': forms.ModelChoiceField(
                label=_('Payment Method'),
                queryset=PaymentMethod.objects
            ),
            'is_recurring': forms.BooleanField(
                label=_('Recurring expense'),
                required=False,
                initial=False,
                widget=forms.CheckboxInput(attrs={
                    'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
                }),
            ),
        }

    def apply_quick_fill(self, option_key: str, form):
        """Apply quick fill option to form using preset FK IDs directly."""
        option = self.quick_fill_menu.get_option(option_key)
        if option:
            form.initial['description'] = option.description
            if option.default_amount:
                form.initial['amount'] = option.default_amount
            if option.category_id:
                form.initial['category'] = option.category_id
            if option.payment_method_id:
                form.initial['payment_method'] = option.payment_method_id
