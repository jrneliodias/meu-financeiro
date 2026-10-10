"""
Service com as regras de negócio para copiar estimativas de um mês anterior.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from django.contrib.auth.models import User

from registers.models import CategoryBudgetEstimate
from registers.repository.budget_estimate_repository import BudgetEstimateRepository


@dataclass(frozen=True)
class CopyItem:
    """Uma linha a copiar: categoria e o valor (possivelmente ajustado pelo usuário)."""
    category_id: int
    amount: Decimal


@dataclass(frozen=True)
class CopyCandidates:
    """Estimativas do mês de origem, separadas pelo que ainda pode ser copiado."""
    source_month: int
    source_year: int
    copyable: List[CategoryBudgetEstimate]
    already_existing: List[CategoryBudgetEstimate]


@dataclass(frozen=True)
class CopyResult:
    created: int
    skipped: int


class BudgetEstimateCopyService:
    """Copia estimativas do último mês anterior com estimativas para um mês de destino."""

    def __init__(self, repository: Optional[BudgetEstimateRepository] = None):
        self.repository = repository or BudgetEstimateRepository()

    def get_copy_candidates(self, user: User, month: int, year: int) -> Optional[CopyCandidates]:
        """Retorna as estimativas do mês de origem, ou None se não houver mês de origem."""
        source = self.repository.find_latest_month_before(user, month, year)
        if source is None:
            return None

        source_month, source_year = source
        existing_category_ids = self.repository.get_category_ids_for_month(user, month, year)

        copyable, already_existing = [], []
        for estimate in self.repository.get_for_month(user, source_month, source_year):
            if estimate.category_id in existing_category_ids:
                already_existing.append(estimate)
            else:
                copyable.append(estimate)

        return CopyCandidates(source_month, source_year, copyable, already_existing)

    def copy_estimates(self, user: User, month: int, year: int, items: List[CopyItem]) -> CopyResult:
        """Cria no mês de destino as linhas copiáveis; nunca sobrescreve as existentes.

        A origem é recalculada aqui (não confia no cliente): categorias fora da origem
        são descartadas e as que já existem no destino contam como `skipped`.
        """
        candidates = self.get_copy_candidates(user, month, year)
        if candidates is None:
            return CopyResult(created=0, skipped=0)

        copyable_ids = {estimate.category_id for estimate in candidates.copyable}
        existing_ids = {estimate.category_id for estimate in candidates.already_existing}

        # Deduplica por categoria: se a mesma categoria vier duas vezes, vale a última.
        items_by_category = {item.category_id: item for item in items}

        to_create = [
            CategoryBudgetEstimate(
                user=user, category_id=item.category_id, amount=item.amount, month=month, year=year,
            )
            for item in items_by_category.values()
            if item.category_id in copyable_ids
        ]
        skipped = sum(1 for category_id in items_by_category if category_id in existing_ids)

        self.repository.bulk_create(to_create)
        return CopyResult(created=len(to_create), skipped=skipped)
