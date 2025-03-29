from typing import Dict, List, NamedTuple
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class BillingPeriod:
    start_date: date
    end_date: date
    billing_month: str


@dataclass
class CategoryExpense:
    name: str
    amount: Decimal
    payment_method: str
    month: str


class MonthlyExpenseReport(NamedTuple):
    month: str
    categories: List[Dict[str, any]]
    total: Decimal
