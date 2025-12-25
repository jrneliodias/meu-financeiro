from typing import Dict, List, NamedTuple, Optional
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class BillingPeriod:
    start_date: date
    end_date: date
    billing_month: str


@dataclass
class CategoryExpense:
    name: str
    amount: Decimal
    payment_method: str
    month: str


class MonthlyExpenseReport(NamedTuple):
    month: str
    categories: List[Dict[str, any]]
    total: Decimal


@dataclass
class InstallmentProgress:
    """
    Represents the progress of an installment payment plan.

    Contains information about paid vs remaining parcels and amounts,
    following the existing dataclass patterns in this module.
    """
    installment_id: int
    description: str
    total_installments: int
    paid_installments: int
    remaining_installments: int
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    progress_percentage: float
    payment_method_name: Optional[str]
    category_name: Optional[str]

    @property
    def is_fully_paid(self) -> bool:
        """Check if all installments have been paid."""
        return self.paid_installments >= self.total_installments

    @property
    def formatted_remaining_amount(self) -> str:
        """Format remaining amount as Brazilian Real (R$ X.XXX,XX)."""
        return self._format_currency(self.remaining_amount)

    @property
    def formatted_total_amount(self) -> str:
        """Format total amount as Brazilian Real (R$ X.XXX,XX)."""
        return self._format_currency(self.total_amount)

    @property
    def formatted_paid_amount(self) -> str:
        """Format paid amount as Brazilian Real (R$ X.XXX,XX)."""
        return self._format_currency(self.paid_amount)

    def _format_currency(self, value: Decimal) -> str:
        """Format decimal value as Brazilian Real currency."""
        if value is None:
            value = Decimal('0.00')
        return "R$ {:,.2f}".format(float(value)).replace(
            ",", "X"
        ).replace(".", ",").replace("X", ".")
