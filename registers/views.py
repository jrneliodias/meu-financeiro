from django.shortcuts import render, redirect
from .forms import ExpenseForm, IncomeForm, CSVImportForm
from .services import ExpenseService, InstallmentService, IncomeService, CSVImportService
from django.contrib import messages
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Expense
import json
import pandas as pd

# Create your views here.

installment_service = InstallmentService()
expense_service = ExpenseService()
income_service = IncomeService()
csv_import_service = CSVImportService()


def register_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(request, 'register/expense_form.html', {'form': form})

        expense_data = form.cleaned_data
        user = request.user

        if not user.is_authenticated:
            messages.error(request, "User isn't logged in")
            # or wherever you want to redirect unauthenticated users

        if expense_data['installments'] > 1:
            installment_service.create_installments(user, expense_data)
            messages.success(
                request, f"{expense_data['installments']} installments have been registered.")
        else:
            expense = expense_service.create_single_expense(user, expense_data)
            messages.success(
                request, f"Expense {expense.__str__()} has been registered.")

        # Redirect after successful POST
        return redirect('register_expense')

    else:
        # Handle quick fill parameter
        quick_fill = request.GET.get('quick_fill')
        form = ExpenseForm(user=request.user)
        if quick_fill:
            form.apply_quick_fill(quick_fill)

    return render(request, 'register/expense_form.html', {'form': form})


def expense_success(request):
    return render(request, 'register/expense_success.html')


def register_income(request):
    if (request.method == 'POST'):
        form = IncomeForm(request.POST)
        if not form.is_valid():
            return render(request, 'register/income_form.html', {'form': form})
        income_data = form.cleaned_data

        user = request.user

        if not user.is_authenticated:
            messages.error(
                request, "user isn't logged in")
            return render(request, 'register/income_form.html', {'form': form})

        income = income_service.create_income(user, income_data)

        return redirect('expense_success')

    else:
        form = IncomeForm()
    return render(request, 'register/income_form.html', {'form': form})


def income_success(request):
    return render(request, 'register/income_success.html')


@login_required
def csv_import(request):
    """Handle CSV file import with preview and validation"""
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            csv_text = form.cleaned_data['csv_text']
            separator = form.cleaned_data['separator']
            skip_header = form.cleaned_data['skip_header']
            auto_create_categories = form.cleaned_data['auto_create_categories']
            auto_create_payment_methods = form.cleaned_data['auto_create_payment_methods']
            preview_mode = form.cleaned_data['preview_mode']
            
            # Parse CSV data - either from file or text input
            if csv_file:
                df, errors = csv_import_service.parse_csv_file(
                    csv_file, separator, skip_header
                )
            else:
                df, errors = csv_import_service.parse_csv_file_from_string(
                    csv_text, separator, skip_header
                )
            
            if df is None:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'register/csv_import.html', {'form': form})
            
            # Show warnings if any
            for error in errors:
                messages.warning(request, error)
            
            if preview_mode:
                # Generate preview data
                preview_data = csv_import_service.preview_data(df)
                
                # Store the DataFrame as CSV string in session for later import
                csv_string = df.to_csv(index=False)
                request.session['csv_import_data'] = {
                    'csv_data': csv_string,
                    'separator': separator,
                    'skip_header': skip_header,
                    'auto_create_categories': auto_create_categories,
                    'auto_create_payment_methods': auto_create_payment_methods,
                    'total_rows': len(df),
                    'columns': list(df.columns)
                }
                
                return render(request, 'register/csv_import_preview.html', {
                    'preview_data': preview_data,
                    'form': form
                })
            else:
                # Import directly
                result = csv_import_service.import_data(
                    df, request.user, auto_create_categories, auto_create_payment_methods
                )
                
                # Show results
                stats = result['stats']
                messages.success(
                    request, 
                    f"Import completed! {stats['imported']} records imported successfully."
                )
                
                if result['errors']:
                    for error in result['errors'][:5]:  # Show first 5 errors
                        messages.error(request, error)
                
                if result['warnings']:
                    for warning in result['warnings'][:5]:  # Show first 5 warnings
                        messages.warning(request, warning)
                
                return redirect('csv_import')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CSVImportForm()
    
    return render(request, 'register/csv_import.html', {'form': form})


@login_required
def csv_import_confirm(request):
    """Confirm and execute CSV import"""
    if request.method == 'POST':
        # Get stored data from session
        import_data = request.session.get('csv_import_data')
        if not import_data:
            messages.error(request, "No import data found. Please upload a file again.")
            return redirect('csv_import')
        
        try:
            # Reconstruct DataFrame from stored CSV data
            import io
            csv_data = import_data['csv_data']
            df = pd.read_csv(io.StringIO(csv_data))
            
            # Import the data
            result = csv_import_service.import_data(
                df, 
                request.user, 
                import_data['auto_create_categories'], 
                import_data['auto_create_payment_methods']
            )
            
            # Clear session data
            if 'csv_import_data' in request.session:
                del request.session['csv_import_data']
            
            # Show results
            stats = result['stats']
            messages.success(
                request, 
                f"Import completed! {stats['imported']} records imported successfully."
            )
            
            if result['errors']:
                for error in result['errors'][:5]:  # Show first 5 errors
                    messages.error(request, error)
            
            if result['warnings']:
                for warning in result['warnings'][:5]:  # Show first 5 warnings
                    messages.warning(request, warning)
            
            return redirect('csv_import')
            
        except Exception as e:
            messages.error(request, f"Error during import: {str(e)}")
            return redirect('csv_import')
    
    return redirect('csv_import')


@csrf_exempt
@require_http_methods(["POST"])
def csv_import_ajax(request):
    """AJAX endpoint for CSV import with progress tracking"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'preview':
            # Handle preview request
            return JsonResponse({
                'status': 'success',
                'message': 'Preview functionality would be implemented here'
            })
        elif action == 'import':
            # Handle import request
            return JsonResponse({
                'status': 'success',
                'message': 'Import functionality would be implemented here'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid action'
            })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        })


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'register/expense_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        quick_fill = self.request.GET.get('quick_fill')
        if quick_fill:
            form.apply_quick_fill(quick_fill)
        return form
