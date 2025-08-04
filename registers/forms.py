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


class CSVImportForm(forms.Form):
    """Form for CSV file import with validation and configuration options"""
    
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Select a CSV file to import. Supported formats: .csv',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400',
            'accept': '.csv'
        })
    )
    
    separator = forms.ChoiceField(
        label='CSV Separator',
        choices=[
            (',', 'Comma (,)'),
            (';', 'Semicolon (;)'),
            ('\t', 'Tab'),
            ('|', 'Pipe (|)'),
        ],
        initial=',',
        help_text='Select the character used to separate columns in your CSV file',
        widget=forms.Select(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500'
        })
    )
    
    skip_header = forms.BooleanField(
        label='Skip Header Row',
        initial=True,
        required=False,
        help_text='Check if your CSV file has a header row that should be skipped',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        })
    )
    
    auto_create_categories = forms.BooleanField(
        label='Auto-create Categories',
        initial=True,
        required=False,
        help_text='Automatically create new categories if they don\'t exist',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        })
    )
    
    auto_create_payment_methods = forms.BooleanField(
        label='Auto-create Payment Methods',
        initial=True,
        required=False,
        help_text='Automatically create new payment methods if they don\'t exist',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        })
    )
    
    preview_mode = forms.BooleanField(
        label='Preview Mode',
        initial=True,
        required=False,
        help_text='Show a preview of the data before importing',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        })
    )

    def clean_csv_file(self):
        """Validate the uploaded CSV file"""
        csv_file = self.cleaned_data.get('csv_file')
        
        if not csv_file:
            raise forms.ValidationError('Please select a CSV file.')
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError('Please upload a valid CSV file.')
        
        # Check file size (limit to 10MB)
        if csv_file.size > 10 * 1024 * 1024:  # 10MB
            raise forms.ValidationError('File size must be less than 10MB.')
        
        return csv_file
