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
