from django import forms
from .models import Expense, Income, Category
from .components.expense_form.expense_form_component import ExpenseFormComponent
from .components.expense_form.quick_fill_menu import QuickFillMenu


class ExpenseForm(forms.ModelForm):
    """Expense form implementing Dependency Inversion"""

    class Meta:
        model = Expense
        fields = ['description', 'amount', 'installment_plan',
                  'date', 'category', 'payment_method']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Initialize quick fill menu and form component
        quick_fill_menu = QuickFillMenu()
        self.form_component = ExpenseFormComponent(user, quick_fill_menu)

        # Update form fields with component configuration
        self.fields.update(self.form_component.get_form_fields())

        # Set initial data if not already set
        if not self.initial:
            self.initial = self.form_component.get_initial_data()

        # Order the category field by name
        self.fields['category'].queryset = Category.objects.order_by('name')

    def apply_quick_fill(self, option_key: str):
        """Apply quick fill option"""
        self.form_component.apply_quick_fill(option_key, self)


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['description', 'amount', 'date', 'category']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }
