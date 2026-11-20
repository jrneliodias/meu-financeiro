"""Recurring expenses and the month's payments."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.timezone import localdate
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import UpdateView

from registers.forms import RecurringExpenseForm
from registers.models import Expense, RecurringExpense
from reports.services.recurring import generate_month, month_overview, set_paid
from utils.dates import YEAR_RANGE, parse_month_year
from utils.http import delete_owned, json_object


@login_required
@require_http_methods(["GET"])
def payment_notifications(request):
    """The month's summary for the bell pop-up (counts + HTML), for the logged-in user only."""
    today = localdate()
    overview = month_overview(request.user, today.year, today.month, today=today)
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
    """The month's payment control for recurring expenses."""
    today = localdate()
    try:
        year, month = parse_month_year(request.GET)
    except ValueError:
        return render(request, 'reports/recurring_payments.html', {
            'filter_error': 'Selecione um mês e ano válidos (%d a %d).' % YEAR_RANGE,
            'selected_month': today.month, 'selected_year': today.year,
        }, status=400)
    return render(request, 'reports/recurring_payments.html', {
        **month_overview(request.user, year, month, today=today),
        'selected_month': month, 'selected_year': year,
    })


@login_required
def recurring_expense_list(request):
    today = localdate()
    return render(request, 'reports/recurring_expense_list.html', {
        'recurring_expenses': (
            RecurringExpense.objects.filter(user=request.user)
            .select_related('category', 'payment_method')
            .annotate(expense_count=Count('recurring_expenses'))
            .order_by('-generate_debit', '-total_amount', 'description')
        ),
        'active_total': RecurringExpense.objects.filter(user=request.user, generate_debit=True).charged_total(),
        'pending_count': month_overview(request.user, today.year, today.month, today=today)['pending_count'],
    })


class RecurringExpenseUpdateView(LoginRequiredMixin, UpdateView):
    form_class = RecurringExpenseForm
    template_name = 'register/recurring_expense_form.html'
    success_url = reverse_lazy('recurring_expense_list')

    def get_queryset(self):
        return RecurringExpense.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        today = localdate()
        return super().get_context_data(month_expense=self.object.month_expense(today.year, today.month), **kwargs)

    def form_valid(self, form):
        """Save; with sync_month=1 also copy the changes onto this month's expense."""
        response = super().form_valid(form)
        today = localdate()
        if self.request.POST.get('sync_month') == '1' and self.object.sync_month_expense(today.year, today.month):
            messages.success(self.request, _("Recurring expense and this month's expense updated successfully."))
        else:
            messages.success(self.request, _("Recurring expense updated successfully."))
        return response


@login_required
@require_http_methods(["POST"])
def recurring_expense_delete(request, pk):
    return delete_owned(request, RecurringExpense.objects, pk,
                        _("Recurring expense '%(description)s' deleted successfully."),
                        _('Recurring expense not found'))


@login_required
@require_http_methods(["POST"])
def recurring_expense_toggle(request, pk):
    """Turn monthly generation (generate_debit) on or off."""
    recurring_expense = RecurringExpense.objects.filter(pk=pk, user=request.user).first()
    if recurring_expense is None:
        return JsonResponse({'error': _('Recurring expense not found')}, status=404)
    recurring_expense.generate_debit = not recurring_expense.generate_debit
    recurring_expense.save()
    return JsonResponse({
        'success': True,
        'generate_debit': recurring_expense.generate_debit,
        'message': (_('Recurring expense activated.') if recurring_expense.generate_debit
                    else _('Recurring expense deactivated.')),
    })


@login_required
@require_http_methods(["POST"])
def recurring_expense_set_paid(request, expense_id):
    """Save the checkbox state of one of the user's recurring occurrences."""
    payload = json_object(request)
    if payload is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    if not isinstance(payload.get('is_paid'), bool):
        return JsonResponse({'error': 'is_paid must be a boolean'}, status=400)
    try:
        expense = set_paid(request.user, expense_id, payload['is_paid'])
    except Expense.DoesNotExist:
        return JsonResponse({'error': _('Expense not found')}, status=404)
    return JsonResponse({'success': True, 'is_paid': expense.is_paid})


@login_required
def recurring_expense_expenses(request, pk):
    """The expenses one recurring expense generated, with payment status."""
    recurring_expense = get_object_or_404(
        RecurringExpense.objects.select_related('category', 'payment_method'), pk=pk, user=request.user,
    )
    expenses = list(recurring_expense.recurring_expenses.select_related('category', 'payment_method')
                    .order_by('-date'))
    return render(request, 'reports/recurring_expense_expenses.html', {
        'recurring_expense': recurring_expense,
        'expenses': expenses,
        'expense_count': len(expenses),
        'total_generated': sum(expense.amount for expense in expenses),
    })


@login_required
@require_http_methods(["GET", "POST"])
def recurring_expense_process(request):
    """Generate the active recurring expenses of a month."""
    today = localdate()
    context = {'month': today.month, 'year': today.year}
    if request.method == 'POST':
        try:
            year, month = parse_month_year(request.POST, required=True)
        except ValueError:
            context['error'] = _('Invalid month and year')
            return render(request, 'reports/recurring_expense_process.html', context, status=400)
        context.update(month=month, year=year, result=generate_month(request.user, year, month))
    return render(request, 'reports/recurring_expense_process.html', context)
