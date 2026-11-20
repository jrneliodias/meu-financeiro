from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from registers.models import Category
from utils.http import json_object

SEARCH_LIMIT = 10


def _category_type(value):
    """'income' or 'expense' (the default) from a request value."""
    return 'income' if value == 'income' else 'expense'


def _json(category):
    return {'id': category.id, 'name': category.name}


@login_required
@require_http_methods(["GET"])
def category_search_ajax(request):
    """Categories whose name contains ?q= (expense by default, income with ?type=income)."""
    categories = Category.objects.filter(
        type=_category_type(request.GET.get('type')), name__icontains=request.GET.get('q', '').strip(),
    )[:SEARCH_LIMIT]
    return JsonResponse({'categories': [_json(category) for category in categories]})


@login_required
@require_http_methods(["POST"])
def category_create_ajax(request):
    """Create a category, or return the existing one with the same name (any case)."""
    data = json_object(request)
    if data is None:
        return JsonResponse({'error': _('Invalid JSON.')}, status=400)
    name, category_type = data.get('name', '').strip(), _category_type(data.get('type'))
    if not name:
        return JsonResponse({'error': _('Category name is required.')}, status=400)
    category = (Category.objects.filter(type=category_type, name__iexact=name).first()
                or Category.objects.create(name=name, type=category_type))
    return JsonResponse({'success': True, 'category': _json(category)})
