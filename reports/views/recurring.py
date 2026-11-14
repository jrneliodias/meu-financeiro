"""Views de despesas recorrentes e pagamentos do mês."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import localdate
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import UpdateView
from registers.forms import RecurringExpenseForm
from registers.models import Expense, RecurringExpense
from reports.services.recurring_expense_service import RecurringExpenseService
from utils.dates import get_all_months_tuples


@login_required
@require_http_methods(["GET"])
def payment_notifications(request):
    """Current-month notification summary scoped to the authenticated user."""
    from django.template.loader import render_to_string
    from reports.services.recurring_payment_service import RecurringPaymentService

    today = localdate()
    overview = RecurringPaymentService().get_overview(
        request.user, today.month, today.year, today=today,
    )
    response = JsonResponse({
        'pending_count': overview['pending_count'],
        'overdue_count': len(overview['overdue_expenses']),
        'html': render_to_string('reports/components/payment_notifications_content.html', {
            **overview, 'today': today,
        }, request=request),
    })
    response['Cache-Control'] = 'no-store'
    return response


@login_required
def recurring_payments(request):
    """Dedicated monthly recurring payment control."""
    from reports.services.recurring_payment_service import RecurringPaymentService

    today = localdate()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
        overview = RecurringPaymentService().get_overview(request.user, month, year)
    except (ValueError, TypeError):
        return render(request, 'reports/recurring_payments.html', {
            'filter_error': 'Selecione um mês e ano válidos (2000 a 2100).',
            'selected_month': today.month, 'selected_year': today.year,
            'all_months': get_all_months_tuples(),
        }, status=400)
    return render(request, 'reports/recurring_payments.html', {
        **overview, 'selected_month': month, 'selected_year': year,
        'all_months': get_all_months_tuples(),
    })


@login_required
def recurring_expense_list(request):
    """List all user's recurring expenses"""
    from utils.dates import get_all_months_tuples, get_current_date

    recurring_expense_service = RecurringExpenseService()
    recurring_expenses = list(
        recurring_expense_service.repository.get_all_recurring_expenses_by_user(request.user)
    )

    # Calculate totals
    active_total = recurring_expense_service.repository.get_total_recurring_expenses_with_debit(request.user)

    current_year, current_month = get_current_date()
    month_status = recurring_expense_service.repository.get_month_expenses_with_status(
        request.user, current_month, current_year
    )
    pending_count = sum(1 for entry in month_status if entry['status'] == 'pending')

    context = {
        'recurring_expenses': recurring_expenses,
        'active_total': active_total,
        'all_months': get_all_months_tuples(),
        'pending_count': pending_count,
    }

    return render(request, 'reports/recurring_expense_list.html', context)


class RecurringExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for recurring expenses"""
    model = RecurringExpense
    form_class = RecurringExpenseForm
    template_name = 'reports/recurring_expense_update.html'
    success_url = '/recurring-expenses/'

    def get_form_kwargs(self):
        """Inject user into form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['month_expense'] = RecurringExpenseService().get_month_expense(
            self.object, localdate())
        return context

    def form_valid(self, form):
        """Save, optionally syncing this month's expense (sync_month=1)."""
        response = super().form_valid(form)
        if self.request.POST.get('sync_month') == '1' and RecurringExpenseService().sync_month_expense(
                self.object, localdate()):
            messages.success(self.request, _("Recurring expense and this month's expense updated successfully."))
        else:
            messages.success(self.request, _("Recurring expense updated successfully."))
        return response


@login_required
@require_http_methods(["POST"])
def recurring_expense_delete(request, pk):
    """Delete recurring expense via AJAX"""
    try:
        recurring_expense_service = RecurringExpenseService()
        recurring_expense = recurring_expense_service.repository.get_recurring_expense_by_id(pk)

        # Verify if user owns the recurring expense
        if recurring_expense.user != request.user:
            return JsonResponse({'error': _('Unauthorized')}, status=403)

        description = recurring_expense.description
        recurring_expense_service.delete_recurring_expense(pk)

        return JsonResponse({
            'success': True,
            'message': _("Recurring expense '%(description)s' deleted successfully.") % {
                'description': description
            }
        })
    except RecurringExpense.DoesNotExist:
        return JsonResponse({'error': _('Recurring expense not found')}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def recurring_expense_toggle(request, pk):
    """Toggle generate_debit field via AJAX"""
    try:
        recurring_expense_service = RecurringExpenseService()
        recurring_expense = recurring_expense_service.repository.get_recurring_expense_by_id(pk)

        # Verify ownership
        if recurring_expense.user != request.user:
            return JsonResponse({'error': _('Unauthorized')}, status=403)

        # Toggle the field
        updated_recurring_expense = recurring_expense_service.toggle_generate_debit(pk)

        return JsonResponse({
            'success': True,
            'generate_debit': updated_recurring_expense.generate_debit,
            'message': (
                _('Recurring expense activated.')
                if updated_recurring_expense.generate_debit
                else _('Recurring expense deactivated.')
            )
        })
    except RecurringExpense.DoesNotExist:
        return JsonResponse({'error': _('Recurring expense not found')}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def recurring_expense_set_paid(request, expense_id):
    """Save the explicit checkbox state for a user-owned occurrence."""
    import json

    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or not isinstance(payload.get('is_paid'), bool):
            return JsonResponse({'error': 'is_paid must be a boolean'}, status=400)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        expense = RecurringExpenseService().set_paid(
            expense_id, request.user, payload['is_paid'],
        )
    except Expense.DoesNotExist:
        return JsonResponse({'error': _('Expense not found')}, status=404)
    return JsonResponse({'success': True, 'is_paid': expense.is_paid})


@login_required
@require_http_methods(["POST"])
def recurring_expense_toggle_paid(request, expense_id):
    """Toggle payment status (is_paid) of a recurring expense's Expense via AJAX"""
    try:
        recurring_expense_service = RecurringExpenseService()
        updated_expense = recurring_expense_service.toggle_paid(expense_id, request.user)

        return JsonResponse({
            'success': True,
            'is_paid': updated_expense.is_paid,
            'message': (
                _('Expense marked as paid.')
                if updated_expense.is_paid
                else _('Expense marked as pending.')
            )
        })
    except Expense.DoesNotExist:
        return JsonResponse({'error': _('Expense not found')}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def recurring_expense_expenses(request, pk):
    """Page listing the expenses generated by one recurring expense, with payment status."""
    recurring_expense = get_object_or_404(
        RecurringExpense.objects.select_related('category', 'payment_method'),
        pk=pk, user=request.user,
    )
    data = RecurringExpenseService().get_recurring_expense_with_expenses(pk)
    return render(request, 'reports/recurring_expense_expenses.html', {
        'recurring_expense': recurring_expense,
        'expenses': data['expenses'],
        'expense_count': data['expense_count'],
        'total_generated': data['total_generated'],
    })


@login_required
@require_http_methods(["POST"])
def process_recurring_expenses_ajax(request):
    """
    AJAX endpoint to process recurring expenses for a selected month/year.
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': _('Invalid request')}, status=400)

    try:
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
    except (TypeError, ValueError):
        return JsonResponse({
            'success': False,
            'error': _('Invalid month and year')
        }, status=400)

    # Process expenses using service
    recurring_expense_service = RecurringExpenseService()
    result = recurring_expense_service.process_recurring_expenses_for_month(
        request.user, month, year
    )

    return JsonResponse(result)
