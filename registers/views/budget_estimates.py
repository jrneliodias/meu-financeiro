from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _, ngettext
from django.views.decorators.http import require_http_methods

from registers.budget_copy import CopyItem, copy_candidates, copy_estimates
from registers.forms import CategoryBudgetEstimateForm, EstimateCopyFormSet
from registers.models import CategoryBudgetEstimate
from utils.dates import parse_month_year


def _list_url(year, month):
    return f"{reverse('budget_estimate_list')}?{urlencode({'month': month, 'year': year})}"


@login_required
def budget_estimate_list(request):
    try:
        year, month = parse_month_year(request.GET)
    except ValueError:
        return HttpResponseBadRequest('Mês/ano inválido')

    form = CategoryBudgetEstimateForm(request.POST or None, instance=CategoryBudgetEstimate(user=request.user),
                                      initial={'month': month, 'year': year})
    if request.method == 'POST' and form.is_valid():
        estimate = form.save()
        messages.success(request, _('Estimate created successfully.'))
        return redirect(_list_url(estimate.year, estimate.month))

    candidates = copy_candidates(request.user, year, month)
    copy_formset, copy_rows = None, []
    if candidates:
        copy_formset = EstimateCopyFormSet(prefix='copy', initial=[
            {'category_id': estimate.category_id, 'selected': True, 'amount': estimate.amount}
            for estimate in candidates.copyable
        ])
        copy_rows = list(zip(copy_formset.forms, candidates.copyable))

    return render(request, 'register/budget_estimate_list.html', {
        'estimates': CategoryBudgetEstimate.objects.filter(user=request.user, month=month, year=year)
                     .select_related('category').order_by('category__name'),
        'form': form,
        'selected_month': month,
        'selected_year': year,
        'copy_candidates': candidates,
        'copy_formset': copy_formset,
        'copy_rows': copy_rows,
    })


@login_required
def budget_estimate_update(request, pk):
    estimate = get_object_or_404(CategoryBudgetEstimate, pk=pk, user=request.user)
    form = CategoryBudgetEstimateForm(request.POST or None, instance=estimate)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _('Estimate updated.'))
        return redirect(_list_url(estimate.year, estimate.month))
    return render(request, 'register/budget_estimate_update.html', {'form': form, 'estimate': estimate})


@login_required
@require_http_methods(["POST"])
def budget_estimate_delete(request, pk):
    estimate = get_object_or_404(CategoryBudgetEstimate, pk=pk, user=request.user)
    estimate.delete()
    messages.success(request, _('Estimate removed.'))
    return redirect(_list_url(estimate.year, estimate.month))


@login_required
@require_http_methods(["POST"])
def budget_estimate_copy(request):
    try:
        year, month = parse_month_year(request.POST, required=True)
    except ValueError:
        return HttpResponseBadRequest()
    redirect_url = _list_url(year, month)

    formset = EstimateCopyFormSet(request.POST, prefix='copy')
    if not formset.is_valid():
        messages.error(request, _('Invalid values. Check the amounts and try again.'))
        return redirect(redirect_url)

    # "Copy all" ignores the checkboxes but keeps the edited amounts.
    copy_all = request.POST.get('action') == 'all'
    rows = [form.cleaned_data for form in formset.forms
            if form.cleaned_data and (copy_all or form.cleaned_data['selected'])]
    if any(row['amount'] is None for row in rows):
        messages.error(request, _('Invalid values. Check the amounts and try again.'))
        return redirect(redirect_url)
    if not rows:
        messages.error(request, _('No estimates selected.'))
        return redirect(redirect_url)

    result = copy_estimates(request.user, year, month, [CopyItem(row['category_id'], row['amount']) for row in rows])
    message = ngettext('%(count)s estimate copied.', '%(count)s estimates copied.', result.created) % {
        'count': result.created}
    if result.skipped:
        message += ' ' + ngettext(
            '%(count)s skipped because it already existed.',
            '%(count)s skipped because they already existed.',
            result.skipped,
        ) % {'count': result.skipped}
    messages.success(request, message)
    return redirect(redirect_url)
