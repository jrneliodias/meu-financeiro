"""
Service para lógica de negócio de entradas (incomes) recentes.
"""

from typing import List, Dict, Any, Optional
from django.contrib.auth.models import User

from registers.repository.recent_income_repository import RecentIncomeRepository


class RecentIncomeService:
    """Service para operações de incomes recentes."""

    def __init__(self, repository: Optional[RecentIncomeRepository] = None):
        self.repository = repository or RecentIncomeRepository()

    def get_recent_incomes(self, user: User) -> List[Dict[str, Any]]:
        """Retorna incomes recentes formatadas para exibição."""
        incomes = self.repository.get_recent_incomes_for_user(user)

        return [
            self._format_income_for_list(income)
            for income in incomes
        ]

    def get_income_for_autofill(
        self,
        income_id: int,
        user: User
    ) -> Optional[Dict[str, Any]]:
        """Retorna dados de uma income formatados para autofill do formulário."""
        income = self.repository.get_income_by_id_for_user(income_id, user)

        if income is None:
            return None

        return self._format_income_for_autofill(income)

    def _format_income_for_list(self, income) -> Dict[str, Any]:
        """Formata income para exibição na lista."""
        return {
            'id': income.id,
            'description': income.description,
            'amount': float(income.amount),
            'amount_formatted': self._format_currency(income.amount),
            'date': income.date.isoformat(),
            'date_formatted': income.date.strftime('%d/%m/%Y'),
            'category_name': income.category.name if income.category else None,
            'category_id': income.category.id if income.category else None,
        }

    def _format_income_for_autofill(self, income) -> Dict[str, Any]:
        """Formata income para preencher o formulário."""
        return {
            'description': income.description,
            'amount': str(income.amount),
            'date': income.date.isoformat(),
            'category_id': income.category.id if income.category else '',
        }

    def _format_currency(self, value) -> str:
        """Formata valor como moeda brasileira (R$ X.XXX,XX)."""
        if value is None:
            return 'R$ 0,00'

        formatted = "R$ {:,.2f}".format(float(value))
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
