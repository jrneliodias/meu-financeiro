"""
Service para lógica de negócio de despesas recentes.

Segue os princípios SOLID:
- Single Responsibility: Apenas lógica de negócio
- Dependency Inversion: Depende de abstração (repository)
- Open/Closed: Extensível sem modificação
"""

from typing import List, Dict, Any, Optional
from django.contrib.auth.models import User

from registers.repository.recent_expense_repository import RecentExpenseRepository
from registers.constants import ExpenseConstants


class RecentExpenseService:
    """
    Service para operações de despesas recentes.

    Responsabilidades:
    - Formatação de dados para exibição
    - Preparação de dados para autofill
    - Orquestração de operações de negócio
    """

    def __init__(self, repository: Optional[RecentExpenseRepository] = None):
        """
        Inicializa o service com dependency injection.

        Args:
            repository: Instância do repository (opcional para testabilidade)
        """
        self.repository = repository or RecentExpenseRepository()

    def get_recent_expenses(self, user: User) -> List[Dict[str, Any]]:
        """
        Retorna despesas recentes formatadas para exibição.

        Args:
            user: Usuário logado

        Returns:
            Lista de dicionários com dados formatados
        """
        expenses = self.repository.get_recent_expenses_for_user(user)

        return [
            self._format_expense_for_list(expense)
            for expense in expenses
        ]

    def get_expense_details(
        self,
        expense_id: int,
        user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Retorna detalhes completos de uma despesa para o modal.

        Args:
            expense_id: ID da despesa
            user: Usuário logado

        Returns:
            Dicionário com detalhes ou None se não encontrada
        """
        expense = self.repository.get_expense_by_id_for_user(expense_id, user)

        if expense is None:
            return None

        return self._format_expense_for_details(expense)

    def get_expense_for_autofill(
        self,
        expense_id: int,
        user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Retorna dados de uma despesa formatados para autofill do formulário.

        Args:
            expense_id: ID da despesa
            user: Usuário logado

        Returns:
            Dicionário com dados do formulário ou None se não encontrada
        """
        expense = self.repository.get_expense_by_id_for_user(expense_id, user)

        if expense is None:
            return None

        return self._format_expense_for_autofill(expense)

    def _format_expense_for_list(self, expense) -> Dict[str, Any]:
        """Formata despesa para exibição na lista."""
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

    def _format_expense_for_details(self, expense) -> Dict[str, Any]:
        """Formata despesa para exibição no modal de detalhes."""
        data = self._format_expense_for_list(expense)

        data.update({
            'is_installment': expense.installment_plan is not None,
            'installment_info': self._get_installment_info(expense),
            'is_recurring': expense.reccurring_expense is not None,
        })

        return data

    def _format_expense_for_autofill(self, expense) -> Dict[str, Any]:
        """Formata despesa para preencher o formulário."""
        return {
            'description': expense.description,
            'amount': str(expense.amount),
            'date': expense.date.isoformat(),
            'category_id': expense.category.id if expense.category else '',
            'category_name': expense.category.name if expense.category else '',
            'payment_method_id': (
                expense.payment_method.id if expense.payment_method else ''
            ),
            'installments': ExpenseConstants.DEFAULT_INSTALLMENTS_COUNT,
        }

    def _get_installment_info(self, expense) -> Optional[Dict[str, Any]]:
        """Retorna informações do parcelamento se existir."""
        if expense.installment_plan is None:
            return None

        installment = expense.installment_plan
        return {
            'description': installment.description,
            'total_installments': installment.total_installments,
            'total_amount': float(installment.total_amount),
            'total_amount_formatted': self._format_currency(installment.total_amount),
        }

    def _format_currency(self, value) -> str:
        """Formata valor como moeda brasileira (R$ X.XXX,XX)."""
        if value is None:
            return 'R$ 0,00'

        formatted = "R$ {:,.2f}".format(float(value))
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
