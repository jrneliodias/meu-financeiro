def format_brl(value):
    """R$ 1.234,56, whatever the active language."""
    return 'R$ {:,.2f}'.format(value).translate(str.maketrans(',.', '.,'))
