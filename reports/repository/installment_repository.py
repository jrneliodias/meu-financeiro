from decimal import Decimal
from typing import List, Optional, Dict, Any
from django.db.models import Count, Sum, Q
from django.contrib.auth.models import User
from registers.models import Installment, Expense


class InstallmentRepository:
    """
    Repository for Installment data access.

    Follows the existing repository pattern with optimized queries
    using select_related and annotate to avoid N+1 queries.
    """

    def get_open_installments_with_progress(
        self,
        reference_month: int,
        reference_year: int,
        user: Optional[User] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all open installments with their payment progress.

        An installment is "open" if it has remaining unpaid expenses
        (expenses with month/year > current month/year).

        Payment logic:
        - Paid if: expense.year < current_year OR
                   (expense.year == current_year AND expense.month <= current_month)

        Args:
            reference_month: Current month (1-12)
            reference_year: Current year
            user: Optional user filter

        Returns:
            List of dictionaries with installment progress data

        Performance: Uses annotations to calculate in single query
        """
        # Build Q objects for paid/unpaid logic
        paid_condition = self._build_paid_condition(reference_month, reference_year)
        unpaid_condition = self._build_unpaid_condition(reference_month, reference_year)

        # Base query with select_related for optimization
        queryset = (
            Installment.objects
            .select_related('category', 'payment_method')
        )

        # Apply user filter if provided
        if user:
            queryset = queryset.filter(user=user)

        # Annotate with paid and unpaid counts
        queryset = queryset.annotate(
            paid_count=Count('expenses', filter=paid_condition),
            unpaid_count=Count('expenses', filter=unpaid_condition),
            paid_sum=Sum('expenses__amount', filter=paid_condition)
        )

        # Filter only open installments (with unpaid expenses)
        queryset = queryset.filter(unpaid_count__gt=0)

        # Order by description for consistent display
        queryset = queryset.order_by('description')

        return self._convert_to_progress_data(queryset)

    def _build_paid_condition(self, reference_month: int, reference_year: int) -> Q:
        """
        Build Q object for paid expenses condition.

        Paid if: year < current_year OR (year == current_year AND month <= current_month)
        """
        return Q(
            Q(expenses__date__year__lt=reference_year) |
            Q(
                expenses__date__year=reference_year,
                expenses__date__month__lte=reference_month
            )
        )

    def _build_unpaid_condition(self, reference_month: int, reference_year: int) -> Q:
        """
        Build Q object for unpaid expenses condition.

        Unpaid if: year > current_year OR (year == current_year AND month > current_month)
        """
        return Q(
            Q(expenses__date__year__gt=reference_year) |
            Q(
                expenses__date__year=reference_year,
                expenses__date__month__gt=reference_month
            )
        )

    def _convert_to_progress_data(self, queryset) -> List[Dict[str, Any]]:
        """
        Convert annotated queryset to progress data dictionaries.

        Separates data transformation from query logic
        following Single Responsibility Principle.
        """
        progress_data = []

        for installment in queryset:
            paid_installments = installment.paid_count or 0
            remaining_installments = installment.total_installments - paid_installments

            # Calculate amounts
            paid_amount = installment.paid_sum or 0
            remaining_amount = installment.total_amount - paid_amount

            # Calculate progress percentage
            has_installments = installment.total_installments > 0
            progress_percentage = (
                (paid_installments / installment.total_installments) * 100
                if has_installments
                else 0.0
            )

            progress_data.append({
                'installment_id': installment.id,
                'description': installment.description,
                'total_installments': installment.total_installments,
                'paid_installments': paid_installments,
                'remaining_installments': remaining_installments,
                'total_amount': installment.total_amount,
                'paid_amount': paid_amount,
                'remaining_amount': remaining_amount,
                'progress_percentage': round(progress_percentage, 1),
                'payment_method_name': (
                    installment.payment_method.name
                    if installment.payment_method else None
                ),
                'category_name': (
                    installment.category.name
                    if installment.category else None
                ),
            })

        # Sort by progress percentage descending (most completed first)
        progress_data.sort(key=lambda x: x['progress_percentage'], reverse=True)

        return progress_data

    def get_open_installment_count(
        self,
        reference_month: int,
        reference_year: int,
        user: Optional[User] = None
    ) -> int:
        """
        Get count of open installments.

        Args:
            reference_month: Current month (1-12)
            reference_year: Current year
            user: Optional user filter

        Returns:
            Number of open installments
        """
        unpaid_condition = self._build_unpaid_condition(reference_month, reference_year)

        queryset = Installment.objects.annotate(
            unpaid_count=Count('expenses', filter=unpaid_condition)
        ).filter(unpaid_count__gt=0)

        if user:
            queryset = queryset.filter(user=user)

        return queryset.count()

    def get_monthly_installment_expenses_total(
        self,
        month: int,
        year: int,
        user: Optional[User] = None,
    ) -> Decimal:
        """Sum of Expense amounts linked to an installment plan for the given month/year."""
        queryset = Expense.objects.filter(
            date__month=month,
            date__year=year,
            installment_plan__isnull=False,
        )
        if user:
            queryset = queryset.filter(user=user)
        result = queryset.aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0')

    def get_monthly_installment_expenses_detail(
        self,
        month: int,
        year: int,
        user=None,
    ):
        """
        Retorna as expenses individuais de parcelas do mês/ano especificado.

        Usado pelo endpoint AJAX do modal do installment_monthly_card.
        Retorna valores via .values() para serialização direta em JSON.
        """
        queryset = Expense.objects.filter(
            date__month=month,
            date__year=year,
            installment_plan__isnull=False,
        ).select_related('category', 'payment_method', 'installment_plan')

        if user:
            queryset = queryset.filter(user=user)

        return queryset.values(
            'id',
            'description',
            'amount',
            'date',
            'category__name',
            'payment_method__name',
            'installment_plan__description',
        ).order_by('-amount', 'description')
