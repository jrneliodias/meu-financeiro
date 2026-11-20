from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _, ngettext
from django.views.decorators.http import require_http_methods

from registers.forms import ExpenseCreateForm
from registers.models import Expense, Installment, QuickFillPreset, RecurringExpense
from utils.http import delete_owned

from . import RECENT_LIMIT


def _create(user, form):
    """Save the expense: as an installment plan, or a single expense (linked to a new recurring one if asked)."""
    data = form.cleaned_data
    if data['installments'] > 1:
        Installment.create_plan(
            user, description=data['description'], total_amount=data['amount'],
            total_installments=data['installments'], start_date=data['date'],
            category=data['category'], payment_method=data['payment_method'],
        )
        return ngettext("%(count)s installment has been registered.",
                        "%(count)s installments have been registered.",
                        data['installments']) % {'count': data['installments']}
    expense = form.save(commit=False)
    expense.user = user
    if data['is_recurring']:
        expense.reccurring_expense = RecurringExpense.start_from(expense)
    expense.save()
    return _("Expense %(expense)s has been registered.") % {'expense': str(expense)}


@login_required
def register_expense(request):
    presets = QuickFillPreset.objects.filter(user=request.user, is_active=True)
    if request.method == 'POST':
        form = ExpenseCreateForm(request.POST)
        if form.is_valid():
            messages.success(request, _create(request.user, form))
            return redirect('register_expense')
    else:
        key = request.GET.get('quick_fill', '')
        form = ExpenseCreateForm(preset=presets.filter(pk=key).first() if key.isdigit() else None)
    return render(request, 'register/expense_form.html', {
        'form': form,
        'quick_fill_presets': presets,
        'recent_expenses': (Expense.objects.filter(user=request.user)
                            .select_related('category').order_by('-updated_at')[:RECENT_LIMIT]),
    })


@login_required
@require_http_methods(["POST"])
def delete_expense(request, pk):
    return delete_owned(request, Expense.objects, pk,
                        _("Expense '%(description)s' deleted successfully."), _('Expense not found'))
