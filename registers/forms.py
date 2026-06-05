from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Expense, Income, Category, RecurringExpense, PaymentMethod, QuickFillPreset, CategoryBudgetEstimate
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

        # Initialize quick fill menu with user for database loading
        quick_fill_menu = QuickFillMenu(user=user)
        self.form_component = ExpenseFormComponent(user, quick_fill_menu)

        # Store quick fill options for template rendering
        self.quick_fill_options = quick_fill_menu.get_all_options_with_keys()

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


class RecurringExpenseForm(forms.ModelForm):
    """Form for recurring expenses with user dependency injection"""

    class Meta:
        model = RecurringExpense
        fields = ['description', 'total_amount', 'start_date',
                  'category', 'payment_method', 'generate_debit']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter only expense type categories
        self.fields['category'].queryset = Category.objects.filter(
            type='expense'
        ).order_by('name')

        # Order payment methods
        self.fields['payment_method'].queryset = PaymentMethod.objects.order_by('name')


class CSVImportForm(forms.Form):
    """Form for CSV file import with validation and configuration options"""
    
    csv_file = forms.FileField(
        label=_('CSV File'),
        required=False,
        help_text=_('Select a CSV file to import. Supported formats: .csv'),
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400',
            'accept': '.csv'
        })
    )
    
    csv_text = forms.CharField(
        label=_('CSV Text'),
        required=False,
        help_text=_('Paste your CSV data directly here. Use this as an alternative to file upload.'),
        widget=forms.Textarea(attrs={
            'class': 'block w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 font-mono p-3',
            'rows': 10,
            'placeholder': 'date,description,amount,category,type,payment_method\n2025-01-15,Grocery Store,45.67,Supermercado,expense,Crédito - Nubank\n2025-01-16,Uber Trip,12.50,Uber,expense,Crédito - Nubank'
        })
    )
    
    separator = forms.ChoiceField(
        label=_('CSV Separator'),
        choices=[
            (',', _('Comma (,)')),
            (';', _('Semicolon (;)')),
            ('\t', _('Tab')),
            ('|', _('Pipe (|)')),
        ],
        initial=',',
        help_text=_('Select the character used to separate columns in your CSV file'),
        widget=forms.Select(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500'
        })
    )
    
    skip_header = forms.BooleanField(
        label=_('Skip Header Row'),
        initial=True,
        required=False,
        help_text=_('Check if your CSV file has a header row that should be skipped'),
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        })
    )
    
    auto_create_categories = forms.BooleanField(
        label=_('Auto-create Categories'),
        initial=True,
        required=False,
        help_text=_("Automatically create new categories if they don't exist"),
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        })
    )
    
    auto_create_payment_methods = forms.BooleanField(
        label=_('Auto-create Payment Methods'),
        initial=True,
        required=False,
        help_text=_("Automatically create new payment methods if they don't exist"),
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        })
    )
    
    preview_mode = forms.BooleanField(
        label=_('Preview Mode'),
        initial=True,
        required=False,
        help_text=_('Show a preview of the data before importing'),
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        })
    )

    def clean_csv_file(self):
        """Validate the uploaded CSV file"""
        csv_file = self.cleaned_data.get('csv_file')
        
        if csv_file:
            # Check file extension
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError(_('Please upload a valid CSV file.'))
            
            # Check file size (limit to 10MB)
            if csv_file.size > 10 * 1024 * 1024:  # 10MB
                raise forms.ValidationError(_('File size must be less than 10MB.'))
        
        return csv_file
    
    def clean_csv_text(self):
        """Validate the CSV text input"""
        csv_text = self.cleaned_data.get('csv_text')
        
        if csv_text:
            # Basic validation - check if it has at least one line with commas
            lines = csv_text.strip().split('\n')
            if len(lines) < 2:  # At least header + one data row
                raise forms.ValidationError(_('CSV text must contain at least 2 lines (header and data).'))
            
            # Check if it looks like CSV (has separators)
            first_line = lines[0]
            if ',' not in first_line and ';' not in first_line and '\t' not in first_line:
                raise forms.ValidationError(_('CSV text does not appear to contain valid separators.'))
        
        return csv_text
    
    def clean(self):
        """Validate that either file or text is provided, but not both"""
        cleaned_data = super().clean()
        csv_file = cleaned_data.get('csv_file')
        csv_text = cleaned_data.get('csv_text')

        if not csv_file and not csv_text:
            raise forms.ValidationError(_('Please provide either a CSV file or CSV text.'))

        if csv_file and csv_text:
            raise forms.ValidationError(_('Please provide either a CSV file OR CSV text, not both.'))

        return cleaned_data


class CSVProcessorForm(forms.Form):
    """Form for CSV processing and transformation (no database writes)"""

    csv_file = forms.FileField(
        label=_('CSV File'),
        required=False,
        help_text=_('Select a CSV file to process. Supported formats: .csv'),
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400',
            'accept': '.csv'
        })
    )

    csv_text = forms.CharField(
        label=_('CSV Text'),
        required=False,
        help_text=_('Paste your CSV data directly here. Use this as an alternative to file upload.'),
        widget=forms.Textarea(attrs={
            'class': 'block w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 font-mono p-3',
            'rows': 10,
            'placeholder': 'Data,Valor,Descrição\n02/11/2024,8.96,Uber - Trip\n02/11/2024,50.00,Supermercado - Compras'
        })
    )

    separator = forms.ChoiceField(
        label=_('CSV Separator'),
        choices=[
            (',', _('Comma (,)')),
            (';', _('Semicolon (;)')),
            ('\t', _('Tab')),
            ('|', _('Pipe (|)')),
        ],
        initial=',',
        help_text=_('Select the character used to separate columns in your CSV file'),
        widget=forms.Select(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500'
        })
    )

    auto_detect = forms.BooleanField(
        label=_('Auto-detect Nubank Format'),
        initial=True,
        required=False,
        help_text=_('Automatically detect Nubank CSV columns (Data, Valor, Description)'),
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600',
            'id': 'id_auto_detect'
        })
    )

    # Manual column mapping fields (shown when auto_detect is False)
    date_column = forms.CharField(
        label=_('Date Column Name'),
        required=False,
        help_text=_('Name of the column containing dates (e.g., "Data")'),
        widget=forms.TextInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500',
            'placeholder': 'Data'
        })
    )

    amount_column = forms.CharField(
        label=_('Amount Column Name'),
        required=False,
        help_text=_('Name of the column containing amounts (e.g., "Valor")'),
        widget=forms.TextInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500',
            'placeholder': 'Valor'
        })
    )

    description_column = forms.CharField(
        label=_('Description Column Name'),
        required=False,
        help_text=_('Name of the column containing descriptions (e.g., "Description")'),
        widget=forms.TextInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500',
            'placeholder': 'Descrição'
        })
    )

    def clean_csv_file(self):
        """Validate the uploaded CSV file"""
        csv_file = self.cleaned_data.get('csv_file')

        if csv_file:
            # Check file extension
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError(_('Please upload a valid CSV file.'))

            # Check file size (limit to 10MB)
            if csv_file.size > 10 * 1024 * 1024:  # 10MB
                raise forms.ValidationError(_('File size must be less than 10MB.'))

        return csv_file

    def clean_csv_text(self):
        """Validate the CSV text input"""
        csv_text = self.cleaned_data.get('csv_text')

        if csv_text:
            # Basic validation - check if it has at least one line
            lines = csv_text.strip().split('\n')
            if len(lines) < 2:  # At least header + one data row
                raise forms.ValidationError(_('CSV text must contain at least 2 lines (header and data).'))

            # Check if it looks like CSV (has separators)
            first_line = lines[0]
            if ',' not in first_line and ';' not in first_line and '\t' not in first_line:
                raise forms.ValidationError(_('CSV text does not appear to contain valid separators.'))

        return csv_text

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        csv_file = cleaned_data.get('csv_file')
        csv_text = cleaned_data.get('csv_text')
        auto_detect = cleaned_data.get('auto_detect')
        date_column = cleaned_data.get('date_column')
        amount_column = cleaned_data.get('amount_column')
        description_column = cleaned_data.get('description_column')

        # Validate that either file or text is provided, but not both
        if not csv_file and not csv_text:
            raise forms.ValidationError(_('Please provide either a CSV file or CSV text.'))

        if csv_file and csv_text:
            raise forms.ValidationError(_('Please provide either a CSV file OR CSV text, not both.'))

        # If auto_detect is disabled, require manual column mapping
        if not auto_detect:
            missing_fields = []
            if not date_column:
                missing_fields.append(str(_('Date Column')))
            if not amount_column:
                missing_fields.append(str(_('Amount Column')))
            if not description_column:
                missing_fields.append(str(_('Description Column')))

            if missing_fields:
                raise forms.ValidationError(
                    _("When auto-detect is disabled, you must specify: %(fields)s") % {
                        'fields': ', '.join(missing_fields)
                    }
                )

        return cleaned_data


class QuickFillPresetForm(forms.ModelForm):
    """Form for creating and editing Quick Fill Presets."""

    class Meta:
        model = QuickFillPreset
        fields = [
            'name', 'description', 'default_amount',
            'category', 'payment_method', 'icon',
            'is_active', 'display_order',
        ]
        widgets = {
            'icon': forms.TextInput(attrs={
                'placeholder': 'fa-car-side',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = Category.objects.filter(
            type='expense'
        ).order_by('name')

        self.fields['payment_method'].queryset = PaymentMethod.objects.order_by('name')


class CategoryBudgetEstimateForm(forms.ModelForm):
    class Meta:
        model = CategoryBudgetEstimate
        fields = ['category', 'amount', 'month', 'year']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'bg-zinc-700 border border-zinc-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'bg-zinc-700 border border-zinc-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'month': forms.Select(attrs={
                'class': 'bg-zinc-700 border border-zinc-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            }, choices=[(i, i) for i in range(1, 13)]),
            'year': forms.NumberInput(attrs={
                'class': 'bg-zinc-700 border border-zinc-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5',
                'min': '2020',
                'max': '2100'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(type='expense').order_by('name')
