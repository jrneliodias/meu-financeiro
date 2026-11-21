def format_brl(value):
    """-R$ 1.234,56 (Intl's pt-BR currency format), whatever the active language.

    The no-break space keeps the symbol and the number on one line.
    """
    number = '{:,.2f}'.format(abs(value)).translate(str.maketrans(',.', '.,'))
    return f"{'-' if value < 0 else ''}R$ {number}"
