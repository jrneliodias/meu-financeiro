from django.shortcuts import render, redirect
from .forms import ExpenseForm, IncomeForm, CSVImportForm, RecurringExpenseForm, CSVProcessorForm, QuickFillPresetForm, CategoryBudgetEstimateForm
from .services import (
    ExpenseService,
    InstallmentService,
    IncomeService,
    CSVImportService,
    RecentExpenseService,
    QuickFillPresetService,
)
from .services.expense_list_service import ExpenseListService
from .constants import ApiStatus, ApiMessages
from .services.csv_processor_service import CSVProcessorService
from reports.services.recurring_expense_service import RecurringExpenseService
from django.contrib import messages
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _, ngettext
from .models import Expense, Category, CategoryBudgetEstimate
import json
import pandas as pd
import io

# Create your views here.

installment_service = InstallmentService()
expense_service = ExpenseService()
income_service = IncomeService()
csv_import_service = CSVImportService()
recent_expense_service = RecentExpenseService()
quick_fill_preset_service = QuickFillPresetService()
expense_list_service = ExpenseListService()


@login_required
def register_expense(request):
    if request.method == 'POST':
        print(f"[DEBUG] POST data received: {request.POST}")
        form = ExpenseForm(request.POST, user=request.user)

        if not form.is_valid():
            print(f"[DEBUG] Form is INVALID. Errors: {form.errors}")
            print(f"[DEBUG] Form errors as dict: {form.errors.as_data()}")
            # Show errors to user
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, _("%(field)s: %(error)s") % {
                        'field': field,
                        'error': error,
                    })
            return render(request, 'register/expense_form.html', {
                'form': form,
                'quick_fill_options': form.quick_fill_options,
            })

        print(f"[DEBUG] Form is VALID. Cleaned data: {form.cleaned_data}")
        expense_data = form.cleaned_data
        user = request.user

        try:
            if expense_data['installments'] > 1:
                print(f"[DEBUG] Creating {expense_data['installments']} installments")
                installment_service.create_installments(user, expense_data)
                messages.success(
                    request,
                    ngettext(
                        "%(count)s installment has been registered.",
                        "%(count)s installments have been registered.",
                        expense_data['installments'],
                    ) % {'count': expense_data['installments']}
                )
            else:
                print(f"[DEBUG] Creating single expense")
                expense = expense_service.create_single_expense(user, expense_data)
                print(f"[DEBUG] Expense created with ID: {expense.id}")
                messages.success(
                    request,
                    _("Expense %(expense)s has been registered.") % {
                        'expense': str(expense)
                    }
                )
        except Exception as e:
            print(f"[DEBUG] ERROR creating expense: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, _("Error creating expense: %(error)s") % {'error': e})
            return render(request, 'register/expense_form.html', {
                'form': form,
                'quick_fill_options': form.quick_fill_options,
            })

        # Redirect after successful POST
        print(f"[DEBUG] Redirecting to register_expense")
        return redirect('register_expense')

    else:
        # Handle quick fill parameter
        quick_fill = request.GET.get('quick_fill')
        form = ExpenseForm(user=request.user)
        if quick_fill:
            form.apply_quick_fill(quick_fill)

    return render(request, 'register/expense_form.html', {
        'form': form,
        'quick_fill_options': form.quick_fill_options,
    })


@login_required
def expense_success(request):
    return render(request, 'register/expense_success.html')


@login_required
def register_income(request):
    if (request.method == 'POST'):
        form = IncomeForm(request.POST)
        if not form.is_valid():
            return render(request, 'register/income_form.html', {'form': form})
        income_data = form.cleaned_data

        user = request.user
        income = income_service.create_income(user, income_data)

        return redirect('expense_success')

    else:
        form = IncomeForm()
    return render(request, 'register/income_form.html', {'form': form})


@login_required
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
                    ngettext(
                        "Import completed! %(count)s record imported successfully.",
                        "Import completed! %(count)s records imported successfully.",
                        stats['imported'],
                    ) % {'count': stats['imported']}
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
                    messages.error(request, _("%(field)s: %(error)s") % {
                        'field': field,
                        'error': error,
                    })
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
            messages.error(request, _("No import data found. Please upload a file again."))
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
                ngettext(
                    "Import completed! %(count)s record imported successfully.",
                    "Import completed! %(count)s records imported successfully.",
                    stats['imported'],
                ) % {'count': stats['imported']}
            )
            
            if result['errors']:
                for error in result['errors'][:5]:  # Show first 5 errors
                    messages.error(request, error)
            
            if result['warnings']:
                for warning in result['warnings'][:5]:  # Show first 5 warnings
                    messages.warning(request, warning)
            
            return redirect('csv_import')
            
        except Exception as e:
            messages.error(request, _("Error during import: %(error)s") % {'error': str(e)})
            return redirect('csv_import')
    
    return redirect('csv_import')


@login_required
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
                'message': _('Preview functionality would be implemented here')
            })
        elif action == 'import':
            # Handle import request
            return JsonResponse({
                'status': 'success',
                'message': _('Import functionality would be implemented here')
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': _('Invalid action')
            })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': _('Invalid JSON data')
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


@login_required
def register_recurring_expense(request):
    """Create new recurring expense"""
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, user=request.user)

        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, _("%(field)s: %(error)s") % {
                        'field': field,
                        'error': error,
                    })
            return render(request, 'register/recurring_expense_form.html', {'form': form})

        recurring_expense_data = form.cleaned_data
        user = request.user

        try:
            recurring_expense_service = RecurringExpenseService()
            recurring_expense = recurring_expense_service.create_recurring_expense(
                user, recurring_expense_data
            )
            messages.success(
                request,
                _("Recurring expense '%(description)s' registered successfully.") % {
                    'description': recurring_expense.description
                }
            )
            return redirect('recurring_expense_list')
        except Exception as e:
            messages.error(request, _("Error creating recurring expense: %(error)s") % {'error': e})
            return render(request, 'register/recurring_expense_form.html', {'form': form})
    else:
        form = RecurringExpenseForm(user=request.user)

    return render(request, 'register/recurring_expense_form.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def delete_expense(request, pk):
    """Delete an individual expense via AJAX"""
    try:
        expense = Expense.objects.get(pk=pk)

        # Verify if user owns the expense
        if expense.user != request.user:
            return JsonResponse({'error': _('Unauthorized')}, status=403)

        description = expense.description
        expense.delete()

        return JsonResponse({
            'success': True,
            'message': _("Expense '%(description)s' deleted successfully.") % {
                'description': description
            }
        })
    except Expense.DoesNotExist:
        return JsonResponse({'error': _('Expense not found')}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def csv_processor(request):
    """CSV Processor - Transform Nubank CSV to standardized format (no database writes)"""
    csv_processor_service = CSVProcessorService()

    if request.method == 'POST':
        form = CSVProcessorForm(request.POST, request.FILES)

        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            csv_text = form.cleaned_data['csv_text']
            separator = form.cleaned_data['separator']
            auto_detect = form.cleaned_data['auto_detect']

            # Parse CSV data - either from file or text input
            if csv_file:
                df, errors = csv_processor_service.parse_csv_file(csv_file, separator)
            else:
                df, errors = csv_processor_service.parse_csv_from_string(csv_text, separator)

            if df is None:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'register/csv_processor.html', {'form': form})

            # Determine column mapping
            column_mapping = None
            if auto_detect:
                column_mapping = csv_processor_service.detect_format(df)
                if column_mapping is None:
                    messages.error(
                        request,
                        _("Could not auto-detect Nubank format. Available columns: %(columns)s") % {
                            'columns': ', '.join(df.columns.tolist())
                        }
                    )
                    return render(request, 'register/csv_processor.html', {'form': form})
            else:
                # Use manual mapping
                column_mapping = {
                    'date': form.cleaned_data['date_column'],
                    'amount': form.cleaned_data['amount_column'],
                    'description': form.cleaned_data['description_column']
                }

            # Process CSV through transformations
            processed_df, warnings = csv_processor_service.process_csv(df, column_mapping)

            if processed_df is None or processed_df.empty:
                messages.error(request, _("Processing failed. No data to display."))
                for warning in warnings:
                    messages.warning(request, warning)
                return render(request, 'register/csv_processor.html', {'form': form})

            # Show warnings if any
            for warning in warnings:
                messages.warning(request, warning)

            # Convert to CSV string for download
            csv_string = csv_processor_service.dataframe_to_csv_string(processed_df)

            # Convert DataFrame to list of dicts for template
            processed_data = processed_df.to_dict('records')

            # Store in session for download and updates
            request.session['processed_csv_data'] = {
                'data': processed_data,
                'csv_string': csv_string,
                'columns': list(processed_df.columns),
                'row_count': len(processed_df),
                'stats': {
                    'total_rows': len(processed_df),
                    'warnings': warnings
                }
            }

            return render(request, 'register/csv_processor_preview.html', {
                'processed_data': processed_data,
                'row_count': len(processed_df),
                'columns': list(processed_df.columns),
                'stats': {
                    'total_rows': len(processed_df),
                    'warnings': warnings
                }
            })
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, _("%(field)s: %(error)s") % {
                        'field': field,
                        'error': error,
                    })
    else:
        form = CSVProcessorForm()

    return render(request, 'register/csv_processor.html', {'form': form})


@login_required
def csv_processor_download(request):
    """Download processed CSV file"""
    # Get csv_string from session
    processed_data = request.session.get('processed_csv_data')

    if not processed_data:
        messages.error(request, _("No processed data found. Please upload and process a file first."))
        return redirect('csv_processor')

    csv_string = processed_data['csv_string']

    # Create HTTP response with CSV content
    response = HttpResponse(csv_string, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="processed_nubank.csv"'
    response['Cache-Control'] = 'no-cache'

    return response


@login_required
@require_http_methods(["POST"])
def csv_processor_update_data(request):
    """AJAX endpoint to update processed CSV data after table edits"""
    try:
        data = json.loads(request.body)
        rows = data.get('rows', [])

        if not rows:
            return JsonResponse({
                'success': False,
                'error': _('No row data provided')
            }, status=400)

        # Update session data
        processed_data = request.session.get('processed_csv_data', {})

        # Update the data
        processed_data['data'] = rows

        # Regenerate CSV string from updated rows
        csv_processor_service = CSVProcessorService()
        df = pd.DataFrame(rows)
        csv_string = csv_processor_service.dataframe_to_csv_string(df)
        processed_data['csv_string'] = csv_string

        # Save back to session
        request.session['processed_csv_data'] = processed_data
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'message': _('Data updated successfully'),
            'row_count': len(rows)
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': _('Invalid JSON data')
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def recent_expenses_ajax(request):
    """AJAX endpoint para listar despesas recentes do usuário."""
    try:
        expenses = recent_expense_service.get_recent_expenses(request.user)

        return JsonResponse({
            'success': True,
            'message': _(ApiMessages.RECENT_EXPENSES_SUCCESS),
            'expenses': expenses,
            'count': len(expenses),
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=ApiStatus.SERVER_ERROR)


@login_required
@require_http_methods(["GET"])
def expense_details_ajax(request, pk):
    """AJAX endpoint para obter detalhes de uma despesa específica."""
    try:
        expense = recent_expense_service.get_expense_details(pk, request.user)

        if expense is None:
            return JsonResponse({
                'success': False,
                'error': _(ApiMessages.EXPENSE_NOT_FOUND),
            }, status=ApiStatus.NOT_FOUND)

        return JsonResponse({
            'success': True,
            'message': _(ApiMessages.DETAILS_SUCCESS),
            'expense': expense,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=ApiStatus.SERVER_ERROR)


@login_required
@require_http_methods(["GET"])
def expense_autofill_ajax(request, pk):
    """AJAX endpoint para obter dados de uma despesa para autofill do formulário."""
    try:
        form_data = recent_expense_service.get_expense_for_autofill(pk, request.user)

        if form_data is None:
            return JsonResponse({
                'success': False,
                'error': _(ApiMessages.EXPENSE_NOT_FOUND),
            }, status=ApiStatus.NOT_FOUND)

        return JsonResponse({
            'success': True,
            'message': _(ApiMessages.AUTOFILL_SUCCESS),
            'form_data': form_data,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=ApiStatus.SERVER_ERROR)


@login_required
@require_http_methods(["GET"])
def expense_list_details_ajax(request):
    """AJAX endpoint para obter lista filtrada de despesas."""
    try:
        filter_type = request.GET.get('filter_type', 'recent')
        filter_value = request.GET.get('filter_value')

        # Get filtered expenses based on filter type
        if filter_type == 'category':
            if not filter_value:
                return JsonResponse({
                    'success': False,
                    'error': _('Category ID is required for category filter'),
                }, status=ApiStatus.BAD_REQUEST)

            expenses = expense_list_service.get_expenses_by_category(
                category_id=int(filter_value),
                user=request.user
            )

            # Get category name for title
            try:
                category = Category.objects.get(id=filter_value)
                filter_title = category.name
            except Category.DoesNotExist:
                filter_title = _('Category not found')

        elif filter_type == 'recent':
            expenses = expense_list_service.get_recent_expenses(request.user)
            filter_title = _('Recent')

        else:
            return JsonResponse({
                'success': False,
                'error': _('Invalid filter type: %(filter_type)s') % {
                    'filter_type': filter_type
                },
            }, status=ApiStatus.BAD_REQUEST)

        # Calculate total amount
        total_amount = sum(exp['amount'] for exp in expenses)

        return JsonResponse({
            'success': True,
            'expenses': expenses,
            'total_amount': float(total_amount),
            'count': len(expenses),
            'filter_info': {
                'type': filter_type,
                'value': filter_title,
                'title': _('Expenses - %(filter_title)s') % {
                    'filter_title': filter_title
                }
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=ApiStatus.SERVER_ERROR)


@login_required
def quick_fill_preset_list(request):
    """List all quick fill presets for the current user."""
    presets = quick_fill_preset_service.get_all_presets_for_user(request.user)
    return render(request, 'register/quick_fill_preset_list.html', {
        'presets': presets,
    })


@login_required
def quick_fill_preset_create(request):
    """Create a new quick fill preset."""
    if request.method == 'POST':
        form = QuickFillPresetForm(request.POST, user=request.user)

        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, _("%(field)s: %(error)s") % {
                        'field': field,
                        'error': error,
                    })
            return render(request, 'register/quick_fill_preset_form.html', {
                'form': form,
                'is_editing': False,
            })

        preset_data = form.cleaned_data
        try:
            preset = quick_fill_preset_service.create_preset(
                request.user, preset_data
            )
            messages.success(
                request,
                _("Preset '%(name)s' created successfully.") % {'name': preset.name}
            )
            return redirect('quick_fill_preset_list')
        except Exception as e:
            messages.error(request, _("Error creating preset: %(error)s") % {'error': e})
            return render(request, 'register/quick_fill_preset_form.html', {
                'form': form,
                'is_editing': False,
            })
    else:
        form = QuickFillPresetForm(user=request.user)

    return render(request, 'register/quick_fill_preset_form.html', {
        'form': form,
        'is_editing': False,
    })


@login_required
def quick_fill_preset_edit(request, pk):
    """Edit an existing quick fill preset."""
    preset = quick_fill_preset_service.get_preset_by_id_for_user(
        pk, request.user
    )
    if preset is None:
        messages.error(request, _("Preset not found."))
        return redirect('quick_fill_preset_list')

    if request.method == 'POST':
        form = QuickFillPresetForm(
            request.POST, instance=preset, user=request.user
        )

        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, _("%(field)s: %(error)s") % {
                        'field': field,
                        'error': error,
                    })
            return render(request, 'register/quick_fill_preset_form.html', {
                'form': form,
                'is_editing': True,
            })

        try:
            form.save()
            messages.success(
                request,
                _("Preset '%(name)s' updated successfully.") % {'name': preset.name}
            )
            return redirect('quick_fill_preset_list')
        except Exception as e:
            messages.error(request, _("Error updating preset: %(error)s") % {'error': e})
            return render(request, 'register/quick_fill_preset_form.html', {
                'form': form,
                'is_editing': True,
            })
    else:
        form = QuickFillPresetForm(instance=preset, user=request.user)

    return render(request, 'register/quick_fill_preset_form.html', {
        'form': form,
        'is_editing': True,
    })


@login_required
@require_http_methods(["POST"])
def quick_fill_preset_delete(request, pk):
    """Delete a quick fill preset via AJAX."""
    try:
        is_deleted = quick_fill_preset_service.delete_preset(pk, request.user)
        if not is_deleted:
            return JsonResponse(
                {'error': _('Preset not found')}, status=404
            )
        return JsonResponse({
            'success': True,
            'message': _('Preset deleted successfully.'),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def category_search_ajax(request):
    """AJAX endpoint to search expense categories by name."""
    search_term = request.GET.get('q', '').strip()
    categories = (
        Category.objects
        .filter(type='expense', name__icontains=search_term)
        .order_by('name')[:10]
    )
    return JsonResponse({
        'categories': [
            {'id': cat.id, 'name': cat.name}
            for cat in categories
        ],
    })


@login_required
@require_http_methods(["POST"])
def category_create_ajax(request):
    """AJAX endpoint to create a new expense category."""
    try:
        data = json.loads(request.body)
        category_name = data.get('name', '').strip()

        if not category_name:
            return JsonResponse(
                {'error': _('Category name is required.')}, status=400
            )

        existing = Category.objects.filter(
            type='expense', name__iexact=category_name
        ).first()
        if existing:
            return JsonResponse({
                'success': True,
                'category': {'id': existing.id, 'name': existing.name},
            })

        category = Category.objects.create(
            name=category_name, type='expense'
        )
        return JsonResponse({
            'success': True,
            'category': {'id': category.id, 'name': category.name},
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON.')}, status=400)


@login_required
def budget_estimate_list(request):
    from datetime import date
    today = date.today()
    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    if request.method == 'POST':
        form = CategoryBudgetEstimateForm(request.POST)
        if form.is_valid():
            estimate = form.save(commit=False)
            estimate.user = request.user
            try:
                estimate.save()
                messages.success(request, _('Estimate created successfully.'))
            except Exception:
                messages.error(request, _('An estimate already exists for this category this month.'))
            return redirect(
                f"{request.path}?month={estimate.month}&year={estimate.year}"
            )
    else:
        form = CategoryBudgetEstimateForm(initial={'month': selected_month, 'year': selected_year})

    estimates = CategoryBudgetEstimate.objects.filter(
        user=request.user, month=selected_month, year=selected_year
    ).select_related('category').order_by('category__name')

    return render(request, 'register/budget_estimate_list.html', {
        'estimates': estimates,
        'form': form,
        'selected_month': selected_month,
        'selected_year': selected_year,
    })


@login_required
def budget_estimate_update(request, pk):
    estimate = CategoryBudgetEstimate.objects.get(pk=pk, user=request.user)
    if request.method == 'POST':
        form = CategoryBudgetEstimateForm(request.POST, instance=estimate)
        if form.is_valid():
            form.save()
            messages.success(request, _('Estimate updated.'))
            return redirect(
                f"/register/estimativas/?month={estimate.month}&year={estimate.year}"
            )
    else:
        form = CategoryBudgetEstimateForm(instance=estimate)

    return render(request, 'register/budget_estimate_update.html', {
        'form': form,
        'estimate': estimate,
    })


@login_required
@require_http_methods(["POST"])
def budget_estimate_delete(request, pk):
    estimate = CategoryBudgetEstimate.objects.get(pk=pk, user=request.user)
    month, year = estimate.month, estimate.year
    estimate.delete()
    messages.success(request, _('Estimate removed.'))
    return redirect(f"/register/estimativas/?month={month}&year={year}")
