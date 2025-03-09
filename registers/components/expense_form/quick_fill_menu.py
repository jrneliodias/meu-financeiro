from dataclasses import dataclass
from typing import List
from decimal import Decimal
from datetime import date


@dataclass
class QuickFillOption:
    """Data class for quick fill options"""
    name: str
    description: str
    category_name: str
    payment_method_name: str
    date: date
    default_amount: Decimal = Decimal('0')


class QuickFillMenu:
    """Quick fill menu component following Open/Closed Principle"""

    def __init__(self):
        self._options = {}
        self._register_default_options()

    def _register_default_options(self):
        """Register default quick fill options"""
        self.register_option('uber', QuickFillOption(
            name='Uber',
            description='Uber Ride',
            category_name='Uber',
            payment_method_name='Crédito - Nubank',
            default_amount=Decimal('10.00'),
            date=date.today()
        ))

    def register_option(self, key: str, option: QuickFillOption):
        """Register a new quick fill option"""
        self._options[key] = option

    def get_option(self, key: str) -> QuickFillOption:
        """Get a quick fill option by key"""
        return self._options.get(key)

    def get_all_options(self) -> List[QuickFillOption]:
        """Get all registered quick fill options"""
        return list(self._options.values())
