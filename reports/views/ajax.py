"""Endpoints AJAX do dashboard (gasto diário, detalhes por data/categoria, parcelas)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext as _
from registers.models import Category
from reports.services.daily_expense_calculator import DailyExpenseCalculator
from ._common import expense_repository


@login_required
def daily_spending_data_ajax(request):
    """
    AJAX endpoint to get daily spending data for different periods.
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': _('Invalid request')}, status=400)

    try:
        # Get the number of days from the request
        days = int(request.GET.get('days', 30))

        # Validate days parameter
        if days not in [7, 30, 60, 90]:
            return JsonResponse({'error': _('Invalid days parameter')}, status=400)

        # Resolve optional category filter
        category = None
        category_id = request.GET.get('category_id', '').strip()
        if category_id:
            try:
                category = Category.objects.get(id=int(category_id), type='expense')
            except (Category.DoesNotExist, ValueError):
                return JsonResponse({'error': _('Invalid category')}, status=400)

        # Create daily calculator and get data
        daily_calculator = DailyExpenseCalculator(expense_repository)
        trend_data = daily_calculator.get_daily_spending_trends(days=days, category=category)

        # Format data for Chart.js
        sorted_dates = sorted(trend_data['daily_expenses'].keys())

        result = {
            'labels': [str(date) for date in sorted_dates],
            'dailyExpenses': [float(trend_data['daily_expenses'][date]) for date in sorted_dates],
            'movingAverages': [float(trend_data['moving_averages'].get(date, 0)) for date in sorted_dates],
            'totalSpending': float(trend_data['total_spending']),
            'averageDaily': float(trend_data['average_daily'])
        }

        return JsonResponse(result)

    except Exception as e:
        print(f"ERROR in daily_spending_data_ajax: {e}")
        import traceback
        print(f"ERROR traceback: {traceback.format_exc()}")

        return JsonResponse({
            'error': _('Failed to load daily spending data'),
            'message': str(e)
        }, status=500)


@login_required
def expense_details_ajax(request):
    """
    AJAX endpoint to get detailed expenses for a specific date.

    Used by the daily spending chart modal to show individual expenses
    when a user clicks on a chart point.

    Returns:
    - List of expenses for the date
    - Total amount for the date
    - Formatted data for modal display
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': _('Invalid request')}, status=400)

    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': _('Date parameter is required')}, status=400)

    try:
        # Parse date string (expected format: YYYY-MM-DD)
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': _('Invalid date format. Expected YYYY-MM-DD')}, status=400)

    try:
        expense_repo = expense_repository
        expenses = expense_repo.get_expenses_by_date(target_date)
        recurring_total = expense_repo.get_recurring_total_by_date(target_date)
        installment_total = expense_repo.get_installment_total_by_date(target_date)
        category_totals = expense_repo.get_category_totals_by_date(target_date)

        # Convert QuerySet to list and ensure JSON serialization
        expenses_list = []
        total_amount = Decimal('0.00')

        for expense in expenses:
            expense_data = {
                'id': expense['id'],
                'description': expense['description'],
                'amount': float(expense['amount']),  # Convert Decimal to float for JSON
                'category': expense['category__name'] or _('Uncategorized'),
                'payment_method': expense['payment_method__name'] or _('No payment method'),
                'created_at': expense['created_at'].strftime('%H:%M') if expense['created_at'] else '',
                'is_recurring': expense['reccurring_expense_id'] is not None,
                'is_installment': expense['installment_plan_id'] is not None,
            }
            expenses_list.append(expense_data)
            total_amount += expense['amount']

        categories = [
            {'category': row['category__name'] or _('Uncategorized'), 'total': float(row['total'])}
            for row in category_totals
        ]

        return JsonResponse({
            'date': date_str,
            'expenses': expenses_list,
            'total_amount': float(total_amount),
            'count': len(expenses_list),
            'formatted_date': target_date.strftime('%d/%m/%Y'),  # Brazilian format
            'recurring_total': float(recurring_total),
            'installment_total': float(installment_total),
            'categories': categories,
        })

    except Exception as e:
        return JsonResponse({
            'error': _('Server error: %(error)s') % {'error': str(e)}
        }, status=500)


# ================================================================================
# Helper Classes for Category Expense Details (Following SOLID Principles)
# ================================================================================

# Helper Class 1: Month Conversion (SRP - Only handles month conversion)
class MonthConverter:
    """
    Converts month names to numbers and vice versa.

    Single Responsibility: Month name/number conversion logic.
    Open/Closed: Can be extended to support multiple locales without modifying existing code.
    """

    MONTH_NAME_TO_NUMBER_MAPPING = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }

    @classmethod
    def convert_name_to_number(cls, month_name: str) -> Optional[int]:
        """
        Convert English month name to month number.

        Args:
            month_name: Month name (e.g., "January")

        Returns:
            Month number (1-12) or None if invalid
        """
        return cls.MONTH_NAME_TO_NUMBER_MAPPING.get(month_name)


# Helper Class 2: Request Validation (SRP - Only validates request data)
class CategoryExpenseRequestValidator:
    """
    Validates incoming AJAX request parameters for category expense details.

    Single Responsibility: Request parameter validation only.
    """

    @staticmethod
    def validate_ajax_request(request) -> Optional[JsonResponse]:
        """
        Validate that the request is a valid AJAX request.

        Returns:
            JsonResponse with error if invalid, None if valid
        """
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': _('Invalid request - AJAX required')}, status=400)
        return None

    @staticmethod
    def validate_required_parameters(
        request_year: Optional[str],
        request_month_name: Optional[str],
        request_category: Optional[str]
    ) -> Optional[JsonResponse]:
        """
        Validate that all required parameters are present.

        Returns:
            JsonResponse with error if validation fails, None if valid
        """
        if not all([request_year, request_month_name, request_category]):
            missing_params = []
            if not request_year:
                missing_params.append(_('year'))
            if not request_month_name:
                missing_params.append(_('month'))
            if not request_category:
                missing_params.append(_('category'))

            return JsonResponse({
                'error': _('Missing required parameters: %(params)s') % {
                    'params': ', '.join(str(param) for param in missing_params)
                }
            }, status=400)
        return None

    @staticmethod
    def validate_month_name(month_name: str):
        """
        Validate month name and convert to number.

        Returns:
            Tuple of (month_number, error_response)
            If valid: (month_number, None)
            If invalid: (None, JsonResponse with error)
        """
        month_number = MonthConverter.convert_name_to_number(month_name)
        if not month_number:
            return None, JsonResponse({
                'error': _('Invalid month name: %(month)s. Expected English month name (e.g., "January")') % {
                    'month': month_name
                }
            }, status=400)
        return month_number, None


# Helper Class 3: Data Formatting (SRP - Only formats expense data for API response)
class CategoryExpenseDataFormatter:
    """
    Formats expense data for JSON API responses.

    Single Responsibility: Data transformation/formatting only.
    """

    @staticmethod
    def format_expense_for_response(expense_record: dict) -> dict:
        """
        Format a single expense record for API response.

        Args:
            expense_record: Raw expense data from database

        Returns:
            Formatted expense data ready for JSON serialization
        """
        return {
            'id': expense_record['id'],
            'date': expense_record['date'].isoformat(),
            'description': expense_record['description'],
            'amount': float(expense_record['amount']),
            'category': expense_record['category__name'] or _('Uncategorized'),
            'payment_method': expense_record['payment_method__name'] or _('N/A'),
            'created_at': expense_record['created_at'].strftime('%H:%M')
        }

    @staticmethod
    def calculate_total_amount(expense_records: list) -> Decimal:
        """
        Calculate total amount from expense records.

        Args:
            expense_records: List of expense dictionaries

        Returns:
            Total amount as Decimal
        """
        total_expense_amount = Decimal('0.00')
        for expense_record in expense_records:
            total_expense_amount += expense_record['amount']
        return total_expense_amount

    @staticmethod
    def build_response_payload(
        request_year: int,
        request_month_name: str,
        request_category: str,
        formatted_expenses: list,
        total_amount: Decimal,
        target_month_number: int
    ) -> dict:
        """
        Build the complete API response payload.

        Returns:
            Dictionary ready for JsonResponse
        """
        return {
            'year': request_year,
            'month': request_month_name,
            'category': request_category,
            'expenses': formatted_expenses,
            'total_amount': float(total_amount),
            'count': len(formatted_expenses),
            'formatted_month': f"{target_month_number:02d}/{request_year}"
        }


@login_required
def category_expense_details_ajax(request):
    """
    AJAX endpoint to get detailed expenses for a specific category and month.

    This view orchestrates the workflow but delegates specific responsibilities
    to helper classes (following Single Responsibility Principle).

    Query Parameters:
        year: Year (YYYY format, e.g., "2024")
        month: Month name (e.g., "January")
        category: Category name (e.g., "Groceries")

    Returns:
        JsonResponse with:
        - expenses: List of expense details
        - total_amount: Sum of all expenses
        - count: Number of expenses
        - formatted_month: MM/YYYY format

    HTTP Status Codes:
        200: Success
        400: Bad request (invalid parameters)
        500: Server error
    """
    # Step 1: Validate AJAX request
    ajax_validation_error = CategoryExpenseRequestValidator.validate_ajax_request(request)
    if ajax_validation_error:
        return ajax_validation_error

    try:
        # Step 2: Extract request parameters with semantic names
        request_year = request.GET.get('year')
        request_month_name = request.GET.get('month')
        request_category = request.GET.get('category')

        # Step 3: Validate required parameters
        parameter_validation_error = CategoryExpenseRequestValidator.validate_required_parameters(
            request_year, request_month_name, request_category
        )
        if parameter_validation_error:
            return parameter_validation_error

        # Step 4: Convert and validate month name
        target_month_number, month_validation_error = CategoryExpenseRequestValidator.validate_month_name(
            request_month_name
        )
        if month_validation_error:
            return month_validation_error

        # Step 5: Fetch expenses from repository (Dependency Inversion - depend on abstraction)
        category_expense_records = expense_repository.get_expenses_by_category_and_month(
            target_year=int(request_year),
            target_month_number=target_month_number,
            category_name_filter=request_category
        )

        # Step 6: Format expenses for response
        formatted_expense_list = []
        for expense_record in category_expense_records:
            formatted_expense = CategoryExpenseDataFormatter.format_expense_for_response(expense_record)
            formatted_expense_list.append(formatted_expense)

        # Step 7: Calculate total amount
        total_expense_amount = CategoryExpenseDataFormatter.calculate_total_amount(
            list(category_expense_records)
        )

        # Step 8: Build complete response payload
        response_payload = CategoryExpenseDataFormatter.build_response_payload(
            request_year=int(request_year),
            request_month_name=request_month_name,
            request_category=request_category,
            formatted_expenses=formatted_expense_list,
            total_amount=total_expense_amount,
            target_month_number=target_month_number
        )

        return JsonResponse(response_payload)

    except ValueError as validation_error:
        return JsonResponse({
            'error': _('Invalid data format: %(error)s') % {
                'error': str(validation_error)
            }
        }, status=400)
    except Exception as unexpected_error:
        # Log the error for debugging (in production, use proper logging)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error fetching category expenses: {unexpected_error}', exc_info=True)

        return JsonResponse({
            'error': _('An unexpected error occurred while fetching expense details')
        }, status=500)


@login_required
def installment_expenses_ajax(request):
    """
    AJAX endpoint para listar as expenses de parcelas do mês selecionado.

    Retorna as expenses individuais que compõem o total exibido no
    installment_monthly_card, permitindo ao usuário verificar o detalhamento.

    Query Parameters:
        month: int (1-12)
        year: int (ex: 2026)

    Returns:
        JsonResponse com:
        - expenses: lista de expenses de parcelas
        - total_amount: soma dos valores
        - count: quantidade de expenses
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': _('Invalid request')}, status=400)

    month_str = request.GET.get('month', '').strip()
    year_str = request.GET.get('year', '').strip()

    if not month_str or not year_str:
        return JsonResponse({'error': _('month and year are required')}, status=400)

    try:
        month = int(month_str)
        year = int(year_str)
    except ValueError:
        return JsonResponse({'error': _('month and year must be integers')}, status=400)

    try:
        from reports.repository.installment_repository import InstallmentRepository
        repo = InstallmentRepository()
        expenses_qs = repo.get_monthly_installment_expenses_detail(
            month=month, year=year, user=request.user
        )

        expenses_list = []
        total_amount = Decimal('0.00')

        for expense in expenses_qs:
            total_amount += expense['amount']
            expenses_list.append({
                'description': expense['description'],
                'amount': float(expense['amount']),
                'date': expense['date'].isoformat(),
                'category': expense['category__name'] or _('Uncategorized'),
                'payment_method': expense['payment_method__name'] or _('N/A'),
                'installment_plan': expense['installment_plan__description'] or '',
            })

        return JsonResponse({
            'month': month,
            'year': year,
            'expenses': expenses_list,
            'total_amount': float(total_amount),
            'count': len(expenses_list),
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error fetching installment expenses: {e}', exc_info=True)
        return JsonResponse({'error': _('An unexpected error occurred')}, status=500)
