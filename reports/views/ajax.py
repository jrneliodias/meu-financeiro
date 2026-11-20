"""AJAX endpoint of the daily spending chart."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext as _

from registers.models import Category
from reports.services.daily import DEFAULT_DAYS, PERIOD_DAYS, daily_spending


@login_required
def daily_spending_data_ajax(request):
    try:
        days = int(request.GET.get('days', DEFAULT_DAYS))
    except ValueError:
        days = None
    if days not in PERIOD_DAYS:
        return JsonResponse({'error': _('Invalid days parameter')}, status=400)

    category = None
    category_id = request.GET.get('category_id', '').strip()
    if category_id:
        category = category_id.isdigit() and Category.objects.expense().filter(id=category_id).first()
        if not category:
            return JsonResponse({'error': _('Invalid category')}, status=400)

    return JsonResponse(daily_spending(request.user, days=days, category=category))
