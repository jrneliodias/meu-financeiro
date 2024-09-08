from django import forms
from .models import Expense, Income


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


class IncomeForm(forms.ModelForm):

    class Meta:
        model = Income
        fields = ['description', 'amount',
                  'date', 'category']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})

        }
