from decimal import ROUND_HALF_UP, Decimal

from django import forms


class ThreePlacesDecimalField(forms.DecimalField):
    """Money amount: up to 3 decimal places; extra digits are rounded, not rejected."""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_digits', 10)
        kwargs.setdefault('decimal_places', 3)
        # step="any" so the browser doesn't reject more than 3 places before we round
        kwargs.setdefault('widget', forms.NumberInput(attrs={'step': 'any'}))
        super().__init__(**kwargs)

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().replace(',', '.')  # ponytail: assumes no thousands separator
        value = super().to_python(value)
        if value is None:
            return value
        return value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
