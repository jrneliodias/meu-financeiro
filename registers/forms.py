from django import forms
from .models import Expense


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
