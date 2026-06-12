from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.contrib.auth.models import User

from reports.services.budget_estimate_service import BudgetEstimateService
from reports.dataclasses import BudgetSummary


class BudgetEstimateServiceWithInstallmentsTest(TestCase):
    """Tests for BudgetEstimateService including monthly installments in total_expected."""

    def _make_service_with_mocks(self, total_fixed, estimates):
        service = BudgetEstimateService()
        service._repo = MagicMock()
        service._recurring_repo = MagicMock()
        service._repo.get_estimates_with_actuals.return_value = estimates
        service._recurring_repo.get_total_recurring_expenses_with_debit.return_value = total_fixed
        return service

    def test_total_expected_inclui_parcelas_do_mes(self):
        service = self._make_service_with_mocks(
            total_fixed=Decimal('500.00'),
            estimates=[],
        )
        user = User(username='test')

        result = service.get_monthly_budget_summary(
            user, month=6, year=2026,
            monthly_installment_total=Decimal('300.00'),
        )

        self.assertEqual(result.total_expected, Decimal('800.00'))

    def test_total_installments_presente_no_budget_summary(self):
        service = self._make_service_with_mocks(
            total_fixed=Decimal('500.00'),
            estimates=[],
        )
        user = User(username='test')

        result = service.get_monthly_budget_summary(
            user, month=6, year=2026,
            monthly_installment_total=Decimal('200.00'),
        )

        self.assertEqual(result.total_installments, Decimal('200.00'))

    def test_sem_parcelas_comportamento_original_mantido(self):
        service = self._make_service_with_mocks(
            total_fixed=Decimal('400.00'),
            estimates=[],
        )
        user = User(username='test')

        result = service.get_monthly_budget_summary(user, month=6, year=2026)

        self.assertEqual(result.total_expected, Decimal('400.00'))
        self.assertEqual(result.total_installments, Decimal('0'))

    def test_total_expected_soma_fixo_mais_parcelas_mais_estimado(self):
        est = MagicMock()
        est.amount = Decimal('150.00')
        est.actual_amount = Decimal('100.00')
        est.category.name = 'Food'

        service = self._make_service_with_mocks(
            total_fixed=Decimal('500.00'),
            estimates=[est],
        )
        user = User(username='test')

        result = service.get_monthly_budget_summary(
            user, month=6, year=2026,
            monthly_installment_total=Decimal('300.00'),
        )

        # 500 (fixed) + 300 (installments) + 150 (estimated) = 950
        self.assertEqual(result.total_expected, Decimal('950.00'))
