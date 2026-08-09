"""
Repository para acesso a dados de entradas (incomes) recentes.

Segue o Repository Pattern com queries otimizadas usando select_related.
"""

from typing import Optional
from django.db.models import QuerySet
from django.contrib.auth.models import User

from registers.models import Income
from registers.constants import ExpenseConstants


class RecentIncomeRepository:
    """Repository para acesso a dados de incomes recentes."""

    def get_recent_incomes_for_user(
        self,
        user: User,
        limit: int = ExpenseConstants.RECENT_EXPENSES_LIMIT
    ) -> QuerySet:
        """
        Retorna as incomes mais recentes do usuário.

        Args:
            user: Usuário logado
            limit: Número máximo de registros (default: 10)

        Returns:
            QuerySet otimizado com select_related
        """
        return (
            Income.objects
            .filter(user=user)
            .select_related('category')
            .order_by('-updated_at')[:limit]
        )

    def get_income_by_id_for_user(
        self,
        income_id: int,
        user: User
    ) -> Optional[Income]:
        """
        Retorna uma income específica com verificação de propriedade.

        Args:
            income_id: ID da income
            user: Usuário logado

        Returns:
            Income se encontrada e pertence ao usuário, None caso contrário
        """
        try:
            return (
                Income.objects
                .select_related('category')
                .get(id=income_id, user=user)
            )
        except Income.DoesNotExist:
            return None
