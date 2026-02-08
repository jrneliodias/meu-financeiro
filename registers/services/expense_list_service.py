"""
Service para lógica de negócio de listagem filtrada de despesas.

Segue os princípios SOLID:
- Single Responsibility: Apenas lógica de negócio para listas de despesas
- Dependency Inversion: Depende de abstração (repository)
- Open/Closed: Extensível sem modificação
"""

from typing import List, Dict, Any
from django.contrib.auth.models import User

from registers.repository.recent_expense_repository import RecentExpenseRepository


class ExpenseListService:
    """
    Service para operações de listagem filtrada de despesas.

    Responsabilidades:
    - Formatação de dados para exibição
    - Filtros por categoria, data, método de pagamento
    - Orquestração de operações de negócio
    """

    def __init__(self, repository: RecentExpenseRepository = None):
        """
        Inicializa o service com dependency injection.

        Args:
            repository: Instância do repository (opcional para testabilidade)
        """
        self.repository = repository or RecentExpenseRepository()

    def get_expenses_by_category(
        self,
        category_id: int,
        user: User,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retorna despesas filtradas por categoria, formatadas para exibição.

        Args:
            category_id: ID da categoria para filtrar
            user: Usuário logado
            limit: Número máximo de registros (default: 50)

        Returns:
            Lista de dicionários com dados formatados
        """
        expenses = self.repository.get_expenses_by_category(
            category_id=category_id,
            user=user,
            limit=limit
        )

        return [
            self._format_expense_for_list(expense)
            for expense in expenses
        ]

    def get_recent_expenses(
        self,
        user: User,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Retorna despesas recentes formatadas para exibição.

        Args:
            user: Usuário logado
            limit: Número máximo de registros (default: 20)

        Returns:
            Lista de dicionários com dados formatados
        """
        expenses = self.repository.get_recent_expenses_for_user(user, limit=limit)

        return [
            self._format_expense_for_list(expense)
            for expense in expenses
        ]

    def _format_expense_for_list(self, expense) -> Dict[str, Any]:
        """
        Formata despesa para exibição na lista.

        Reutiliza o mesmo formato da RecentExpenseService para consistência.

        Args:
            expense: Objeto Expense do Django

        Returns:
            Dicionário com dados formatados
        """
        return {
            'id': expense.id,
            'description': expense.description,
            'amount': float(expense.amount),
            'amount_formatted': self._format_currency(expense.amount),
            'date': expense.date.isoformat(),
            'date_formatted': expense.date.strftime('%d/%m/%Y'),
            'category_name': expense.category.name if expense.category else None,
            'category_id': expense.category.id if expense.category else None,
            'payment_method_name': (
                expense.payment_method.name if expense.payment_method else None
            ),
            'payment_method_id': (
                expense.payment_method.id if expense.payment_method else None
            ),
        }

    def _format_currency(self, value) -> str:
        """
        Formata valor como moeda brasileira (R$ X.XXX,XX).

        Args:
            value: Valor numérico (Decimal ou float)

        Returns:
            String formatada no padrão brasileiro
        """
        if value is None:
            return 'R$ 0,00'

        formatted = "R$ {:,.2f}".format(float(value))
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
