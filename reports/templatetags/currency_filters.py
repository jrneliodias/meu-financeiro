from django import template
from django.utils.translation import gettext as _

register = template.Library()


@register.filter
def format_brl(value):
    """
    Formats a float value into Brazilian Real currency format (R$ 1.234,90).
    """
    try:
        # Ensure value has two decimal places and replace the decimal and thousand separators
        formatted_value = "R$ {:,.2f}".format(value).replace(
            ",", "X").replace(".", ",").replace("X", ".")
        return formatted_value
    except (ValueError, TypeError):
        return "R$ 0,00"  # Return a default value if formatting fails


@register.filter
def get_item(dictionary, key):
    """
    Gets an item from a dictionary using the key.
    Usage: {{ my_dict|get_item:my_key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def translate_month(month_name):
    """Translate English month names used internally for display."""
    month_translations = {
        'January': _('January'),
        'February': _('February'),
        'March': _('March'),
        'April': _('April'),
        'May': _('May'),
        'June': _('June'),
        'July': _('July'),
        'August': _('August'),
        'September': _('September'),
        'October': _('October'),
        'November': _('November'),
        'December': _('December'),
    }
    return month_translations.get(month_name, month_name)
