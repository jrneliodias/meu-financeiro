"""
Repository module for registers application.

Provides data access layer following the Repository Pattern.
"""

from .recent_expense_repository import RecentExpenseRepository

__all__ = ['RecentExpenseRepository']
