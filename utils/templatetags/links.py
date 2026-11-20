from urllib.parse import urlencode

from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def url_returning(context, url_name, **params):
    """URL of `url_name` with `params` in the query plus back=<current page>, for pages with a back link."""
    params['back'] = context['request'].get_full_path()
    return f'{reverse(url_name)}?{urlencode(params)}'
