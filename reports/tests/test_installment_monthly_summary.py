from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, Expense, Installment, PaymentMethod
from reports.repository.installment_repository import InstallmentRepository
from reports.services.installment_progress_calculator import InstallmentProgressCalculator


class InstallmentMonthlyTotalRepositoryTest(TestCase):
    """Tests for InstallmentRepository.get_monthly_installment_expenses_total."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.category = Category.objects.create(name='Electronics', type='expense')
        self.payment_method = PaymentMethod.objects.create(
            name='Credit Card', start_billing_day=10
        )
        self.installment = Installment.objects.create(
            user=self.user,
            description='iPhone 15',
            total_amount=Decimal('3000.00'),
            total_installments=12,
            start_date=date(2026, 1, 1),
            category=self.category,
            payment_method=self.payment_method,
        )
        self.repo = InstallmentRepository()

    def test_soma_apenas_expenses_de_parcelas_no_mes(self):
        Expense.objects.create(
            user=self.user, description='iPhone 15 - 1/12',
            amount=Decimal('250.00'), date=date(2026, 6, 10),
            installment_plan=self.installment,
        )
        Expense.objects.create(
            user=self.user, description='iPhone 15 - 2/12',
            amount=Decimal('250.00'), date=date(2026, 6, 15),
            installment_plan=self.installment,
        )
        # Esta expense não tem parcela — não deve entrar no total
        Expense.objects.create(
            user=self.user, description='Almoço',
            amount=Decimal('50.00'), date=date(2026, 6, 10),
            installment_plan=None,
        )

        total = self.repo.get_monthly_installment_expenses_total(
            month=6, year=2026, user=self.user
        )

        self.assertEqual(total, Decimal('500.00'))

    def test_retorna_zero_quando_sem_parcelas_no_mes(self):
        total = self.repo.get_monthly_installment_expenses_total(
            month=6, year=2026, user=self.user
        )

        self.assertEqual(total, Decimal('0'))

    def test_ignora_expenses_de_outros_meses(self):
        Expense.objects.create(
            user=self.user, description='iPhone 15 - 1/12',
            amount=Decimal('250.00'), date=date(2026, 5, 10),
            installment_plan=self.installment,
        )

        total = self.repo.get_monthly_installment_expenses_total(
            month=6, year=2026, user=self.user
        )

        self.assertEqual(total, Decimal('0'))

    def test_ignora_expenses_de_outro_usuario(self):
        other_user = User.objects.create_user(username='other', password='pass')
        other_installment = Installment.objects.create(
            user=other_user, description='TV',
            total_amount=Decimal('1200.00'), total_installments=6,
            start_date=date(2026, 1, 1),
        )
        Expense.objects.create(
            user=other_user, description='TV - 1/6',
            amount=Decimal('200.00'), date=date(2026, 6, 10),
            installment_plan=other_installment,
        )

        total = self.repo.get_monthly_installment_expenses_total(
            month=6, year=2026, user=self.user
        )

        self.assertEqual(total, Decimal('0'))


class InstallmentProgressCalculatorMonthlyTest(TestCase):
    """Tests for InstallmentProgressCalculator.get_monthly_installment_summary."""

    def test_retorna_dict_com_total_amount_e_formatted_total(self):
        mock_repo = MagicMock(spec=InstallmentRepository)
        mock_repo.get_monthly_installment_expenses_total.return_value = Decimal('150.00')

        calculator = InstallmentProgressCalculator(installment_repository=mock_repo)
        result = calculator.get_monthly_installment_summary(month=6, year=2026)

        self.assertEqual(result['total_amount'], Decimal('150.00'))
        self.assertIn('R$', result['formatted_total'])
        mock_repo.get_monthly_installment_expenses_total.assert_called_once_with(
            6, 2026, None
        )

    def test_formatted_total_quando_zero(self):
        mock_repo = MagicMock(spec=InstallmentRepository)
        mock_repo.get_monthly_installment_expenses_total.return_value = Decimal('0')

        calculator = InstallmentProgressCalculator(installment_repository=mock_repo)
        result = calculator.get_monthly_installment_summary(month=6, year=2026)

        self.assertEqual(result['total_amount'], Decimal('0'))
        self.assertIn('R$', result['formatted_total'])

    def test_passa_user_para_repositorio(self):
        user = User(username='testuser')
        mock_repo = MagicMock(spec=InstallmentRepository)
        mock_repo.get_monthly_installment_expenses_total.return_value = Decimal('0')

        calculator = InstallmentProgressCalculator(installment_repository=mock_repo)
        calculator.get_monthly_installment_summary(month=6, year=2026, user=user)

        mock_repo.get_monthly_installment_expenses_total.assert_called_once_with(
            6, 2026, user
        )


class GetMonthlyInstallmentExpensesDetailTest(TestCase):
    """Tests para InstallmentRepository.get_monthly_installment_expenses_detail."""

    def setUp(self):
        self.user = User.objects.create_user(username='detailuser', password='pass')
        self.category = Category.objects.create(name='Eletronicos', type='expense')
        self.payment_method = PaymentMethod.objects.create(
            name='Nubank', start_billing_day=10
        )
        self.installment = Installment.objects.create(
            user=self.user,
            description='iPhone 15',
            total_amount=Decimal('6000.00'),
            total_installments=12,
            start_date=date(2026, 1, 1),
            category=self.category,
            payment_method=self.payment_method,
        )
        self.expense = Expense.objects.create(
            user=self.user,
            description='iPhone 15 3/12',
            amount=Decimal('500.00'),
            date=date(2026, 6, 15),
            category=self.category,
            payment_method=self.payment_method,
            installment_plan=self.installment,
        )
        self.repo = InstallmentRepository()

    def test_retorna_expenses_de_parcelas_do_mes(self):
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['description'], 'iPhone 15 3/12')
        self.assertEqual(result[0]['installment_plan__description'], 'iPhone 15')

    def test_exclui_outros_meses(self):
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=5, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 0)

    def test_exclui_expenses_sem_parcela(self):
        Expense.objects.create(
            user=self.user,
            description='Almoço avulso',
            amount=Decimal('50.00'),
            date=date(2026, 6, 10),
            installment_plan=None,
        )
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 1)

    def test_exclui_expenses_de_outro_usuario(self):
        other_user = User.objects.create_user(username='outro', password='pass')
        other_installment = Installment.objects.create(
            user=other_user,
            description='TV',
            total_amount=Decimal('1200.00'),
            total_installments=6,
            start_date=date(2026, 1, 1),
        )
        Expense.objects.create(
            user=other_user,
            description='TV 1/6',
            amount=Decimal('200.00'),
            date=date(2026, 6, 10),
            installment_plan=other_installment,
        )
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 1)

    def test_ordena_por_amount_decrescente(self):
        Expense.objects.create(
            user=self.user,
            description='iPhone 15 4/12',
            amount=Decimal('800.00'),
            date=date(2026, 6, 20),
            installment_plan=self.installment,
        )
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        self.assertEqual(len(result), 2)
        self.assertGreaterEqual(result[0]['amount'], result[1]['amount'])

    def test_retorna_campos_obrigatorios(self):
        result = list(self.repo.get_monthly_installment_expenses_detail(
            month=6, year=2026, user=self.user
        ))
        row = result[0]
        for field in ('id', 'description', 'amount', 'date',
                      'category__name', 'payment_method__name',
                      'installment_plan__description'):
            self.assertIn(field, row)
