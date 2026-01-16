"""
Repository para acesso a dados de despesas recentes.

Segue o Repository Pattern com queries otimizadas usando select_related.
Single Responsibility: Apenas operações de acesso a dados.
"""

from typing import Optional
from django.db.models import QuerySet
from django.contrib.auth.models import User

from registers.models import Expense
from registers.constants import ExpenseConstants


class RecentExpenseRepository:
    """
    Repository para acesso a dados de despesas recentes.

    Responsabilidades:
    - Queries otimizadas com select_related
    - Filtragem por usuário
    - Ordenação por data/criação
    """

    def get_recent_expenses_for_user(
        self,
        user: User,
        limit: int = ExpenseConstants.RECENT_EXPENSES_LIMIT
    ) -> QuerySet:
        """
        Retorna as despesas mais recentes do usuário.

        Args:
            user: Usuário logado
            limit: Número máximo de registros (default: 10)

        Returns:
            QuerySet otimizado com select_related

        Performance: Usa select_related para evitar N+1 queries
        """
        return (
            Expense.objects
            .filter(user=user)
            .select_related('category', 'payment_method')
            .order_by('-date', '-id')[:limit]
        )

    def get_expense_by_id_for_user(
        self,
        expense_id: int,
        user: User
    ) -> Optional[Expense]:
        """
        Retorna uma despesa específica com verificação de propriedade.

        Args:
            expense_id: ID da despesa
            user: Usuário logado

        Returns:
            Expense se encontrada e pertence ao usuário, None caso contrário
        """
        try:
            return (
                Expense.objects
                .select_related('category', 'payment_method', 'installment_plan')
                .get(id=expense_id, user=user)
            )
        except Expense.DoesNotExist:
            return None
