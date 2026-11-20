from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from registers.forms import IncomeForm
from registers.models import Income
from utils.http import delete_owned

from . import RECENT_LIMIT


@login_required
def register_income(request):
    form = IncomeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        income = form.save(commit=False)
        income.user = request.user
        income.save()
        messages.success(request, _("Income %(income)s has been registered.") % {'income': str(income)})
        return redirect('register_income')
    return render(request, 'register/income_form.html', {
        'form': form,
        'recent_incomes': (Income.objects.filter(user=request.user)
                           .select_related('category').order_by('-updated_at')[:RECENT_LIMIT]),
    })


@login_required
@require_http_methods(["POST"])
def delete_income(request, pk):
    return delete_owned(request, Income.objects, pk,
                        _("Income '%(description)s' deleted successfully"), _("Income not found"))
