"""Copy category estimates from the latest earlier month that has any into a target month."""
from dataclasses import dataclass
from decimal import Decimal
from typing import List

from django.db.models import Q

from .models import CategoryBudgetEstimate


@dataclass(frozen=True)
class CopyItem:
    """One row to copy: category and the (possibly user-edited) amount."""
    category_id: int
    amount: Decimal


@dataclass(frozen=True)
class CopyCandidates:
    """The source month's estimates, split by whether the target month already has that category."""
    source_year: int
    source_month: int
    copyable: List[CategoryBudgetEstimate]
    already_existing: List[CategoryBudgetEstimate]


@dataclass(frozen=True)
class CopyResult:
    created: int
    skipped: int


def copy_candidates(user, year, month):
    """Estimates of the latest month before month/year that has any, or None if there is none."""
    mine = CategoryBudgetEstimate.objects.filter(user=user)
    source = (mine.filter(Q(year__lt=year) | Q(year=year, month__lt=month))
              .order_by('-year', '-month').values('month', 'year').first())
    if source is None:
        return None
    existing_ids = set(mine.filter(month=month, year=year).values_list('category_id', flat=True))
    copyable, already_existing = [], []
    for estimate in (mine.filter(month=source['month'], year=source['year'])
                     .select_related('category').order_by('category__name')):
        (already_existing if estimate.category_id in existing_ids else copyable).append(estimate)
    return CopyCandidates(source['year'], source['month'], copyable, already_existing)


def copy_estimates(user, year, month, items):
    """Create the copyable `items` in month/year; never overwrite existing ones.

    The source is recomputed here (the client isn't trusted): categories outside it are dropped
    and the ones that already exist in the target count as skipped.
    """
    candidates = copy_candidates(user, year, month)
    if candidates is None:
        return CopyResult(created=0, skipped=0)
    copyable_ids = {estimate.category_id for estimate in candidates.copyable}
    existing_ids = {estimate.category_id for estimate in candidates.already_existing}
    items_by_category = {item.category_id: item for item in items}  # the same category twice: the last wins
    to_create = [
        CategoryBudgetEstimate(user=user, category_id=item.category_id, amount=item.amount, month=month, year=year)
        for item in items_by_category.values() if item.category_id in copyable_ids
    ]
    CategoryBudgetEstimate.objects.bulk_create(to_create)
    return CopyResult(created=len(to_create), skipped=sum(1 for c in items_by_category if c in existing_ids))
