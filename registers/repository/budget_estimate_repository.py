"""
Repository para acesso a dados de estimativas de orçamento por categoria.
"""

from typing import List, Optional, Set, Tuple

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from registers.models import CategoryBudgetEstimate


class BudgetEstimateRepository:
    """Consultas de CategoryBudgetEstimate, sempre filtradas por usuário."""

    def get_for_month(self, user: User, month: int, year: int) -> QuerySet:
        """Estimativas do mês, com a categoria carregada, ordenadas pelo nome da categoria."""
        return (
            CategoryBudgetEstimate.objects
            .filter(user=user, month=month, year=year)
            .select_related('category')
            .order_by('category__name')
        )

    def find_latest_month_before(self, user: User, month: int, year: int) -> Optional[Tuple[int, int]]:
        """(month, year) mais recente estritamente anterior ao informado que tenha estimativas."""
        latest = (
            CategoryBudgetEstimate.objects
            .filter(user=user)
            .filter(Q(year__lt=year) | Q(year=year, month__lt=month))
            .order_by('-year', '-month')
            .values('month', 'year')
            .first()
        )
        if latest is None:
            return None
        return latest['month'], latest['year']

    def get_category_ids_for_month(self, user: User, month: int, year: int) -> Set[int]:
        """IDs das categorias que já têm estimativa no mês."""
        return set(
            CategoryBudgetEstimate.objects
            .filter(user=user, month=month, year=year)
            .values_list('category_id', flat=True)
        )

    def bulk_create(self, estimates: List[CategoryBudgetEstimate]) -> List[CategoryBudgetEstimate]:
        """Cria todas de uma vez; o Django executa o bulk_create dentro de uma transação."""
        return CategoryBudgetEstimate.objects.bulk_create(estimates)
