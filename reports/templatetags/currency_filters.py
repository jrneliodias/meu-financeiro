from django import template

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
