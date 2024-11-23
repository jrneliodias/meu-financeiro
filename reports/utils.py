
from decimal import Decimal


def convert_values_to_float(data):
    return {key: float(value) if isinstance(
        value, Decimal) else float(value) for key, value in data.items()}
