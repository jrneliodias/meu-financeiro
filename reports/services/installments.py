from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db.models import Count, Q, Sum

from registers.models import Installment
from utils.dates import month_end


@dataclass
class InstallmentProgress:
    description: str
    total_installments: int
    paid_installments: int
    total_amount: Decimal
    paid_amount: Decimal
    payment_method_name: Optional[str]
    category_name: Optional[str]

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

    @property
    def progress_percentage(self):
        if not self.total_installments:
            return 0.0
        return round(self.paid_installments / self.total_installments * 100, 1)


def open_installments(user, year, month):
    """Plans with expenses after month/year; an expense dated up to that month counts as paid."""
    end = month_end(year, month)
    paid = Q(expenses__date__lte=end)
    plans = (
        Installment.objects.filter(user=user)
        .select_related('category', 'payment_method')
        .annotate(
            paid_count=Count('expenses', filter=paid),
            unpaid_count=Count('expenses', filter=Q(expenses__date__gt=end)),
            paid_sum=Sum('expenses__amount', filter=paid),
        )
        .filter(unpaid_count__gt=0)
        .order_by('description')
    )
    progress = sorted(
        (InstallmentProgress(
            description=plan.description,
            total_installments=plan.total_installments,
            paid_installments=plan.paid_count,
            total_amount=plan.total_amount,
            paid_amount=plan.paid_sum or Decimal('0'),
            payment_method_name=plan.payment_method.name if plan.payment_method else None,
            category_name=plan.category.name if plan.category else None,
        ) for plan in plans),
        key=lambda item: item.progress_percentage, reverse=True,
    )
    return {
        'count': len(progress),
        'total_remaining': sum((item.remaining_amount for item in progress), Decimal('0')),
        'installments': progress,
    }
