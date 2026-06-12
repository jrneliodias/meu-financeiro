from typing import List, Optional, Dict, Any
from decimal import Decimal
from django.contrib.auth.models import User

from reports.repository.installment_repository import InstallmentRepository
from reports.dataclasses import InstallmentProgress


class InstallmentProgressCalculator:
    """
    Calculator service for installment progress following SOLID principles.

    Handles calculation and processing of installment payment progress data.
    Uses dependency injection for better testability.
    """

    def __init__(self, installment_repository: Optional[InstallmentRepository] = None):
        """
        Initialize calculator with dependency injection.

        Args:
            installment_repository: Repository instance for data access
        """
        self.repository = installment_repository or InstallmentRepository()

    def get_open_installments_progress(
        self,
        reference_month: int,
        reference_year: int,
        user: Optional[User] = None
    ) -> List[InstallmentProgress]:
        """
        Get progress data for all open installments.

        Args:
            reference_month: Current month (1-12)
            reference_year: Current year
            user: Optional user filter

        Returns:
            List of InstallmentProgress dataclass instances
        """
        raw_data = self.repository.get_open_installments_with_progress(
            reference_month=reference_month,
            reference_year=reference_year,
            user=user
        )

        return [
            self._create_progress_dataclass(item)
            for item in raw_data
        ]

    def _create_progress_dataclass(self, data: Dict[str, Any]) -> InstallmentProgress:
        """
        Create InstallmentProgress dataclass from dictionary data.

        Factory method for clean dataclass instantiation.
        """
        return InstallmentProgress(
            installment_id=data['installment_id'],
            description=data['description'],
            total_installments=data['total_installments'],
            paid_installments=data['paid_installments'],
            remaining_installments=data['remaining_installments'],
            total_amount=Decimal(str(data['total_amount'])),
            paid_amount=Decimal(str(data['paid_amount'])),
            remaining_amount=Decimal(str(data['remaining_amount'])),
            progress_percentage=float(data['progress_percentage']),
            payment_method_name=data.get('payment_method_name'),
            category_name=data.get('category_name'),
        )

    def get_installments_summary(
        self,
        reference_month: int,
        reference_year: int,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics for installments.

        Args:
            reference_month: Current month (1-12)
            reference_year: Current year
            user: Optional user filter

        Returns:
            Dictionary with count, total remaining, formatted values, and installments list
        """
        progress_list = self.get_open_installments_progress(
            reference_month=reference_month,
            reference_year=reference_year,
            user=user
        )

        total_remaining = sum(
            item.remaining_amount for item in progress_list
        )
        total_installments_count = len(progress_list)

        return {
            'count': total_installments_count,
            'total_remaining': total_remaining,
            'formatted_total_remaining': self._format_currency(total_remaining),
            'installments': progress_list,
        }

    def get_monthly_installment_summary(
        self,
        month: int,
        year: int,
        user: Optional[User] = None,
    ) -> dict:
        """Total installment spending for the selected month/year."""
        total = self.repository.get_monthly_installment_expenses_total(month, year, user)
        return {
            'total_amount': total,
            'formatted_total': self._format_currency(total),
        }

    def _format_currency(self, value: Decimal) -> str:
        """
        Format value as Brazilian Real currency.

        Args:
            value: Decimal value to format

        Returns:
            Formatted currency string (R$ X.XXX,XX)
        """
        if value is None:
            value = Decimal('0.00')

        formatted_value = "R$ {:,.2f}".format(float(value)).replace(
            ",", "X"
        ).replace(".", ",").replace("X", ".")

        return formatted_value
