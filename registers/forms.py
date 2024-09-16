from django import forms
from .models import Expense, Income, Category


class ExpenseForm(forms.ModelForm):
    installments = forms.IntegerField(
        min_value=1, initial=1, label='Number of Installments')

    class Meta:
        model = Expense
        fields = ['description', 'amount', 'installments',
                  'date', 'category', 'payment_method']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})

        }

    def __init__(self, *args, **kwargs):
        super(ExpenseForm, self).__init__(*args, **kwargs)

        # Order the category field by name
        self.fields['category'].queryset = Category.objects.order_by('name')


class IncomeForm(forms.ModelForm):

    class Meta:
        model = Income
        fields = ['description', 'amount',
                  'date', 'category']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})

        }
