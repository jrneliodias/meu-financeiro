import io

from django import forms
from django.forms import formset_factory
from django.utils.dates import MONTHS
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from utils.dates import YEAR_RANGE

from .fields import ThreePlacesDecimalField
from .models import (
    Category, CategoryBudgetEstimate, Expense, Income, Installment, PaymentMethod, QuickFillPreset, RecurringExpense,
)

INPUT_CLASS = 'w-full px-3 bg-transparent py-2 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
SELECT_CLASS = INPUT_CLASS + ' appearance-none *:bg-zinc-900'
CHECKBOX_CLASS = 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, attrs=None):
        super().__init__(attrs, format='%Y-%m-%d')


class StyledForm:
    """Gives every widget the app's input, select or checkbox classes unless it sets its own."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = (CHECKBOX_CLASS if isinstance(widget, forms.CheckboxInput)
                   else SELECT_CLASS if isinstance(widget, forms.Select) else INPUT_CLASS)
            widget.attrs.setdefault('class', css)


LABELS = {
    'description': _('Description'), 'amount': _('Amount'), 'date': _('Date'),
    'category': _('Category'), 'payment_method': _('Payment Method'),
}


class ExpenseForm(StyledForm, forms.ModelForm):
    """Edit an expense; the create form adds installments and the recurring flag."""
    amount = ThreePlacesDecimalField(label=_('Amount'))

    class Meta:
        model = Expense
        fields = ['description', 'amount', 'date', 'category', 'payment_method']
        widgets = {'date': DateInput()}
        labels = LABELS


class ExpenseCreateForm(ExpenseForm):
    installments = forms.IntegerField(label=_('Installments'), min_value=1, max_value=Installment.MAX_INSTALLMENTS,
                                      initial=1)
    is_recurring = forms.BooleanField(label=_('Recurring expense'), required=False)

    def __init__(self, *args, preset=None, **kwargs):
        """`preset`: a QuickFillPreset whose values pre-fill the form."""
        super().__init__(*args, **kwargs)
        self.initial.setdefault('date', localdate())
        if preset:
            self.initial['description'] = preset.description
            for field, value in [('amount', preset.default_amount), ('category', preset.category_id),
                                 ('payment_method', preset.payment_method_id)]:
                if value:
                    self.initial[field] = value

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('is_recurring') and cleaned_data.get('installments', 1) > 1:
            raise forms.ValidationError(
                _('A recurring expense cannot be split into installments. Choose only one option.')
            )
        return cleaned_data


class IncomeForm(StyledForm, forms.ModelForm):
    amount = ThreePlacesDecimalField(label=_('Amount'))

    class Meta:
        model = Income
        fields = ['description', 'amount', 'date', 'category']
        widgets = {'date': DateInput()}
        labels = LABELS


class RecurringExpenseForm(StyledForm, forms.ModelForm):
    class Meta:
        model = RecurringExpense
        fields = ['description', 'total_amount', 'start_date',
                  'category', 'payment_method', 'generate_debit', 'is_international']
        widgets = {'start_date': DateInput()}
        labels = {**LABELS, 'total_amount': _('Amount'), 'start_date': _('Start Date'),
                  'generate_debit': _('Generate Monthly Debit'), 'is_international': _('International (adds 3.5% IOF)')}


class QuickFillPresetForm(StyledForm, forms.ModelForm):
    class Meta:
        model = QuickFillPreset
        fields = ['name', 'description', 'default_amount', 'category', 'payment_method',
                  'icon', 'is_active', 'display_order']
        widgets = {'icon': forms.TextInput(attrs={'placeholder': 'fa-car-side'})}
        labels = {**LABELS, 'name': _('Name (Button Label)'), 'default_amount': _('Default Amount'),
                  'icon': _('Icon (FontAwesome)'), 'is_active': _('Active'), 'display_order': _('Display Order')}
        help_texts = {'icon': _('e.g. fa-car-side, fa-utensils, fa-shopping-cart')}


class CategoryBudgetEstimateForm(StyledForm, forms.ModelForm):
    """Create with `instance=CategoryBudgetEstimate(user=…)`: the user is needed to check duplicates."""
    month = forms.TypedChoiceField(label=_('Month'), choices=MONTHS.items(), coerce=int)
    year = forms.IntegerField(label=_('Year'), min_value=YEAR_RANGE[0], max_value=YEAR_RANGE[1])

    class Meta:
        model = CategoryBudgetEstimate
        fields = ['category', 'amount', 'month', 'year']
        widgets = {'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'})}
        labels = {'category': _('Category'), 'amount': _('Estimated Amount (R$)')}

    def clean(self):
        cleaned_data = super().clean()
        duplicate = CategoryBudgetEstimate.objects.filter(
            user=self.instance.user, category=cleaned_data.get('category'),
            month=cleaned_data.get('month'), year=cleaned_data.get('year'),
        ).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError(_('An estimate already exists for this category this month.'))
        return cleaned_data


class EstimateCopyRowForm(StyledForm, forms.Form):
    """One row of the estimate copy: category, whether it was ticked and the amount to use."""
    category_id = forms.IntegerField(widget=forms.HiddenInput)
    selected = forms.BooleanField(required=False)
    # Optional here: only the rows being copied need it (the view checks).
    amount = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
    )


EstimateCopyFormSet = formset_factory(EstimateCopyRowForm, extra=0)


class CSVSourceForm(StyledForm, forms.Form):
    """CSV given as an uploaded file or pasted text (exactly one), plus its separator."""
    MAX_FILE_SIZE = 10 * 1024 * 1024

    csv_file = forms.FileField(
        label=_('CSV File'), required=False,
        help_text=_('Select a CSV file to import. Supported formats: .csv'),
        widget=forms.FileInput(attrs={'accept': '.csv'}),
    )
    csv_text = forms.CharField(
        label=_('CSV Text'), required=False,
        help_text=_('Paste your CSV data directly here. Use this as an alternative to file upload.'),
        widget=forms.Textarea(attrs={'rows': 10, 'class': INPUT_CLASS + ' font-mono'}),
    )
    separator = forms.ChoiceField(
        label=_('CSV Separator'),
        choices=[(',', _('Comma (,)')), (';', _('Semicolon (;)')), ('\t', _('Tab')), ('|', _('Pipe (|)'))],
        initial=',',
        help_text=_('Select the character used to separate columns in your CSV file'),
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError(_('Please upload a valid CSV file.'))
            if csv_file.size > self.MAX_FILE_SIZE:
                raise forms.ValidationError(_('File size must be less than 10MB.'))
        return csv_file

    def clean(self):
        cleaned_data = super().clean()
        csv_file, csv_text = cleaned_data.get('csv_file'), cleaned_data.get('csv_text')
        if not csv_file and not csv_text:
            raise forms.ValidationError(_('Please provide either a CSV file or CSV text.'))
        if csv_file and csv_text:
            raise forms.ValidationError(_('Please provide either a CSV file OR CSV text, not both.'))
        if csv_text:
            lines = csv_text.strip().split('\n')
            if len(lines) < 2:
                self.add_error('csv_text', _('CSV text must contain at least 2 lines (header and data).'))
            elif cleaned_data.get('separator') not in lines[0]:
                self.add_error('csv_text', _('CSV text does not appear to contain valid separators.'))
        return cleaned_data

    def source(self):
        """The uploaded file or the pasted text, ready for pandas.read_csv."""
        return self.cleaned_data['csv_file'] or io.StringIO(self.cleaned_data['csv_text'])


class CSVImportForm(CSVSourceForm):
    auto_create_categories = forms.BooleanField(
        label=_('Auto-create Categories'), initial=True, required=False,
        help_text=_("Automatically create new categories if they don't exist"),
    )
    auto_create_payment_methods = forms.BooleanField(
        label=_('Auto-create Payment Methods'), initial=True, required=False,
        help_text=_("Automatically create new payment methods if they don't exist"),
    )
    preview_mode = forms.BooleanField(
        label=_('Preview Mode'), initial=True, required=False,
        help_text=_('Show a preview of the data before importing'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['csv_text'].widget.attrs['placeholder'] = (
            'date,description,amount,category,type,payment_method\n'
            '2025-01-15,Grocery Store,45.67,Supermercado,expense,Crédito - Nubank\n'
            '2025-01-16,Uber Trip,12.50,Uber,expense,Crédito - Nubank'
        )


class CSVProcessorForm(CSVSourceForm):
    """Nubank export → standard CSV (no database writes)."""
    auto_detect = forms.BooleanField(
        label=_('Auto-detect Nubank Format'), initial=True, required=False,
        help_text=_('Automatically detect Nubank CSV columns (Data, Valor, Description)'),
    )
    # Manual column mapping, shown when auto_detect is off
    date_column = forms.CharField(
        label=_('Date Column Name'), required=False,
        help_text=_('Name of the column containing dates (e.g., "Data")'),
        widget=forms.TextInput(attrs={'placeholder': 'Data'}),
    )
    amount_column = forms.CharField(
        label=_('Amount Column Name'), required=False,
        help_text=_('Name of the column containing amounts (e.g., "Valor")'),
        widget=forms.TextInput(attrs={'placeholder': 'Valor'}),
    )
    description_column = forms.CharField(
        label=_('Description Column Name'), required=False,
        help_text=_('Name of the column containing descriptions (e.g., "Description")'),
        widget=forms.TextInput(attrs={'placeholder': 'Descrição'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['csv_file'].help_text = _('Select a CSV file to process. Supported formats: .csv')
        self.fields['csv_text'].widget.attrs['placeholder'] = (
            'Data,Valor,Descrição\n02/11/2024,8.96,Uber - Trip\n02/11/2024,50.00,Supermercado - Compras'
        )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('auto_detect'):
            missing = [str(label) for field, label in [
                ('date_column', _('Date Column')), ('amount_column', _('Amount Column')),
                ('description_column', _('Description Column')),
            ] if not cleaned_data.get(field)]
            if missing:
                raise forms.ValidationError(
                    _("When auto-detect is disabled, you must specify: %(fields)s") % {'fields': ', '.join(missing)}
                )
        return cleaned_data

    def column_mapping(self):
        """{'date': …, 'amount': …, 'description': …} source column names, or None to auto-detect."""
        if self.cleaned_data['auto_detect']:
            return None
        return {target: self.cleaned_data[f'{target}_column'] for target in ('date', 'amount', 'description')}
