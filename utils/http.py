import json

from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme


def safe_return_url(request, param):
    """`param` from POST or GET when it points back into this site, else ''."""
    url = request.POST.get(param) or request.GET.get(param) or ''
    return url if url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}) else ''


def json_object(request):
    """The request body as a JSON object (dict), or None when it is not one."""
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def delete_owned(request, queryset, pk, deleted_message, not_found_message):
    """Delete the user's record `pk` from `queryset` and answer in JSON (404 when it isn't theirs).

    `deleted_message` may use %(description)s.
    """
    record = queryset.filter(pk=pk, user=request.user).first()
    if record is None:
        return JsonResponse({'error': not_found_message}, status=404)
    record.delete()
    return JsonResponse({'success': True, 'message': deleted_message % {'description': getattr(record, 'description', '')}})
