from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from registers.forms import RecurringExpenseForm


@login_required
def register_recurring_expense(request):
    form = RecurringExpenseForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            recurring_expense = form.save(commit=False)
            recurring_expense.user = request.user
            recurring_expense.save()
            messages.success(request, _("Recurring expense '%(description)s' registered successfully.") % {
                'description': recurring_expense.description
            })
            return redirect('recurring_expense_list')
    return render(request, 'register/recurring_expense_form.html', {'form': form})
