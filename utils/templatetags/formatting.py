from django import template
from django.utils.html import format_html
from django.utils.dates import MONTHS

from utils import money
from utils.dates import YEAR_RANGE

register = template.Library()


@register.filter
def format_brl(value):
    """Blank (not a believable R$ 0,00) when the value isn't a number, e.g. a misspelled variable."""
    try:
        return money.format_brl(value)
    except (TypeError, ValueError):
        return ''


@register.simple_tag
def year_bounds():
    """'min="…" max="…"' for year inputs: the years parse_month_year accepts."""
    return format_html('min="{}" max="{}"', *YEAR_RANGE)


@register.simple_tag
def month_choices():
    """[(1, 'Janeiro'), …] in the active language, for month <select>s."""
    return list(MONTHS.items())


@register.filter
def at(sequence, index):
    """sequence[index], for lists indexed by a loop counter."""
    return sequence[index]


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
