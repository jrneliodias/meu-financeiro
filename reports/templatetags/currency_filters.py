import locale
from django import template

register = template.Library()

# Set the locale for Brazilian Real (BRL)
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')


@register.filter(name='brl_currency')
def brl_currency(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    return locale.currency(value, grouping=True, symbol='R$ ')
