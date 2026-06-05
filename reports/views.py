from django.shortcuts import render
from collections import defaultdict
import calendar
from datetime import datetime, date as date_type
from decimal import Decimal
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from reports.repository import ExpenseRepository, IncomeRepository, CategoryRepository
from reports.services import ExpenseService, BalanceService, BudgetEstimateService
from reports.services.recurring_expense_service import RecurringExpenseService
from django.views.generic import UpdateView
from registers.models import Category, Expense, Income, PaymentMethod, RecurringExpense
from registers.forms import ExpenseForm, RecurringExpenseForm
from utils.dates import get_all_months, get_current_date, get_all_months_tuples
from django.http import JsonResponse
from reports.services.daily_expense_calculator import DailyExpenseCalculator
from reports.services.installment_progress_calculator import InstallmentProgressCalculator
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from typing import Optional
expense_repository = ExpenseRepository()
installment_calculator = InstallmentProgressCalculator()
income_repository = IncomeRepository()
category_repository = CategoryRepository()
balance_service = BalanceService()
recurring_expense_service = RecurringExpenseService()
budget_estimate_service = BudgetEstimateService()


def index(request):
    return render(request, 'core/index.html')


@login_required
def expense_report(request):
    """
    Optimized expense report view using consolidated database queries.

    Performance improvements:
    - Single aggregated query for expenses by category and payment method
    - Single aggregated query for incomes by month
    - Eliminated N+1 queries with select_related/prefetch_related
    - Reduced from ~50+ queries to 3-5 queries total
    """
    # Get the current year and month
    current_year, current_month = get_current_date()
    distinct_years = expense_repository.get_distinct_years_in_tuples()
    distinct_months = get_all_months_tuples()

    # Get the selected year and month from the request
    selected_year, selected_month, selected_month_name = get_selected_year_and_month(
        request, current_year, current_month)

    # Create expense service with selected year
    expense_service = ExpenseService(
        expense_repository, income_repository, year=selected_year
    )

    # Get all months for template
    all_months = get_all_months()

    # OPTIMIZED: Use service methods instead of standalone functions
    # 1. Get expense data with single aggregated query
    optimized_expenses = expense_service.get_optimized_expenses_data(all_months)

    # Format data for template
    formatted_expenses_by_category = {}
    for category, month_totals in optimized_expenses['expenses_by_category_by_month'].items():
        formatted_expenses_by_category[category] = [
            format_brl(month_totals.get(month, 0.0))
            for month in all_months
        ]

    formatted_totals = [
        format_brl(optimized_expenses['total_expense_by_month'].get(month, 0.0))
        for month in all_months
    ]

    # 2. Get income data with single query
    incomes_by_month = expense_service.get_optimized_incomes_by_month(all_months)

    # 3. Get payment method data with consolidated queries
    payment_method_data = expense_service.get_optimized_payment_method_data()

    # 4. Get monthly expenses with proper select_related (no N+1)
    monthly_expenses_queryset = expense_service.get_optimized_monthly_expenses(selected_month)

    # Calculate global balance (keep existing logic as it's already optimized)
    global_balance = balance_service.calculate_global_balance()

    # Get daily spending data
    daily_spending_data = get_daily_spending_data(
        expense_repository, selected_year, selected_month
    )

    # 5. Get fixed expenses summary
    fixed_expenses_summary = recurring_expense_service.get_fixed_expenses_summary()

    # 6. Get installment progress data
    installments_progress = installment_calculator.get_installments_summary(
        reference_month=selected_month,
        reference_year=selected_year
    )

    # 7. Get today's total expenses for the daily card
    today = date_type.today()
    today_total = float(expense_repository.get_total_by_date(today))
    today_date = today.strftime('%Y-%m-%d')

    # 8. Get budget estimates summary for selected month/year
    budget_summary = budget_estimate_service.get_monthly_budget_summary(
        request.user, selected_month, selected_year
    )

    # Prepare the context
    context = {
        'all_months': all_months,
        'formatted_expenses_by_category': formatted_expenses_by_category,
        'formatted_totals': formatted_totals,
        'incomes_by_month': incomes_by_month,
        'categories': get_distinct_categories(),
        'expense_categories': Category.objects.filter(type='expense').order_by('name'),
        'current_year': current_year,
        'distinct_years': distinct_years,
        'distinct_months': distinct_months,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_month_name': selected_month_name,
        'monthy_payment_method_expense_totals': payment_method_data['monthly_totals'],
        'calculated_monthy_payment_method_expense_totals': payment_method_data['datasets'],
        'monthly_expense_income_datasets': payment_method_data['combined_datasets'],
        'monthly_expenses_queryset': monthly_expenses_queryset,
        'global_balance': global_balance,
        'daily_spending_data': daily_spending_data,
        'fixed_expenses_summary': fixed_expenses_summary,
        'installments_progress': installments_progress,
        'today_total': today_total,
        'today_date': today_date,
        'budget_summary': budget_summary,
    }

    return render(request, 'reports/expense_report.html', context)


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'reports/expense_update.html'
    success_url = '/'

    def get_form_kwargs(self):
        """Inject user into form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        """Remove installments field for edit form."""
        form = super().get_form(form_class)
        # installments field is only for creation, not editing
        if 'installments' in form.fields:
            del form.fields['installments']
        return form

    def form_valid(self, form):
        """Save and add success message."""
        messages.success(self.request, "Expense updated successfully.")
        return super().form_valid(form)


def process_monthly_expenses(monthly_reports, all_months):
    """Process monthly expense reports and return structured data."""
    expenses_by_category_by_month = defaultdict(
        lambda: {month: 0.0 for month in all_months})
    total_expense_by_month = {month: 0.0 for month in all_months}
    total_expense_by_month_list = {month: 'R$ 0,00' for month in all_months}

    for report in monthly_reports:
        # Process categories
        for category in report.categories:
            expenses_by_category_by_month[category['name']
                                          ][report.month] = category['total_amount']

        # Process totals
        total_expense_by_month[report.month] = float(report.total)
        total_expense_by_month_list[report.month] = format_brl(report.total)

    return {
        'by_category': dict(expenses_by_category_by_month),
        'totals': total_expense_by_month,
        'formatted_totals': total_expense_by_month_list
    }


def get_payment_method_data(expense_service, current_year):
    """Get payment method related data."""
    return {
        'totals': expense_service.monthly_payment_method_expense_totals(current_year),
        'calculated_totals': expense_service.calculate_monthly_payment_method_total_expense_datasets()
    }


def get_monthly_data(expense_service, selected_year, selected_month):
    """Get monthly expense and income data."""
    return {
        'expense_total': expense_service.calculate_monthly_expenses_total(),
        'expense_income_datasets': expense_service.create_month_total_datasets(),
        'expenses_queryset': get_expenses_by_month(selected_year, selected_month)
    }


def format_data_for_template(expenses_data, all_months):
    """Format expense data for template display."""
    formatted_expenses_by_category = {}
    for category, month_totals in expenses_data['by_category'].items():
        formatted_expenses_by_category[category] = [
            format_brl(month_totals.get(month, 0.0))
            for month in all_months
        ]

    formatted_totals = [
        format_brl(expenses_data['totals'].get(month, 0.0))
        for month in all_months
    ]

    return {
        'expenses_by_category': formatted_expenses_by_category,
        'totals': formatted_totals
    }


def get_expenses_by_month_and_category(year):
    """
    Returns expenses categorized by month and category for the given year.
    """
    expenses = expense_repository.get_expenses_for_year(year)
    months_in_database = expense_repository.get_months_in_list()

    expenses_by_category = build_expenses_by_category(expenses)
    total_expense_by_month = calculate_total_expense_by_month(expenses)

    fill_missing_months(expenses_by_category, months_in_database)

    return (
        sort_category_by_month(expenses_by_category),
        sort_by_month(total_expense_by_month),
        format_total_expenses(total_expense_by_month)
    )


def build_expenses_by_category(expenses):
    """Build a nested dictionary of expenses by category and month."""
    expenses_by_category = defaultdict(lambda: defaultdict(float))
    for expense in expenses:
        month = expense['month'].strftime('%B')
        category = expense['category__name']
        total = float(expense['total_amount'])
        expenses_by_category[category][month] = format_brl(total)
    return expenses_by_category


def calculate_total_expense_by_month(expenses):
    """Calculate the total expense for each month."""
    total_by_month = defaultdict(float)
    for expense in expenses:
        month = expense['month'].strftime('%B')
        total_by_month[month] += float(expense['total_amount'])
    return total_by_month


def fill_missing_months(expenses_by_category, months_in_database):
    """Fill missing months with 0.00 in each category."""
    for months in expenses_by_category.values():
        for month in months_in_database:
            if month not in months:
                months[month] = 0.00


def format_total_expenses(total_expense_by_month):
    """Format total expenses for each month."""
    return {month: format_brl(amount) for month, amount in total_expense_by_month.items()}


def get_incomes_by_month(year):
    """Returns a dictionary where onths as keys and the total income for that month as values."""
    income_by_month_query_set = income_repository.get_incomes_by_month(year)

    income_by_month_dict = format_incomes_by_month_in_dict(
        income_by_month_query_set)

    month_list = expense_repository.get_months_in_list()

    income_by_month_dict_filled = format_empty_incomes_by_month_in_dict(
        income_by_month_dict, month_list)

    return income_by_month_dict_filled


def format_incomes_by_month_in_dict(income_by_month_query_set):

    income_by_month_dict = {item['month'].strftime('%B'): float(
        item['total_amount']) for item in list(income_by_month_query_set)}

    return income_by_month_dict


def format_empty_incomes_by_month_in_dict(income_by_month_dict, month_list):
    income_by_month_dict_filled = {
        label: income_by_month_dict.get(label, 0.0) for label in month_list}
    return income_by_month_dict_filled


def get_expenses_by_selected_month(year, month):
    """Returns total expenses grouped by category for a specific month of a given year."""
    if month:
        return expense_repository.get_expenses_group_by_category_and_month(
            year, month
        )
    return []


def get_selected_year_and_month(request, default_year, default_month):
    """Extracts selected year and month from the request or defaults to the current year and month."""
    selected_year = int(request.GET.get('year', default_year))
    selected_month = int(request.GET.get('month', default_month))
    selected_month_name = calendar.month_name[selected_month]

    return selected_year, selected_month, selected_month_name


def get_distinct_categories():
    """Returns distinct category names."""
    return category_repository.get_categories()


def sort_category_by_month(data):
    # Define the correct order of months
    month_order = expense_repository.get_months_in_list()

    # Function to sort a dictionary based on the month order
    sorted_data = {}
    for category, months in data.items():
        # Sort the months based on the predefined month order
        sorted_months = dict(
            sorted(months.items(), key=lambda x: month_order.index(x[0])))
        sorted_data[category] = sorted_months

    return sorted_data


def sort_by_month(data):
    # Define the correct order of months
    month_order = expense_repository.get_months_in_list()

    sorted_data = dict(
        sorted(data.items(), key=lambda x: month_order.index(x[0])))
    return sorted_data


def get_expenses_by_month(year, month):

    return expense_repository.get_monthly_expenses_by_year(year, month)


def format_brl(value):
    """
    Formats a float value into Brazilian Real currency format (R$ 1.234,90).
    """
    # Ensure value has two decimal places and replace the decimal and thousand separators
    formatted_value = "R$ {:,.2f}".format(value).replace(
        ",", "X").replace(".", ",").replace("X", ".")
    return formatted_value


def get_daily_spending_data(expense_repository, year, month):
    """
    Get daily spending data for the chart.

    Why separate function? Maintains the modular approach of your existing code
    and makes testing easier.
    """
    try:
        daily_calculator = DailyExpenseCalculator(expense_repository, year, month)

        # Get trend data for the last 30 days
        trend_data = daily_calculator.get_daily_spending_trends(days=30)

        # Format data for Chart.js - ensure all values are JSON-serializable
        sorted_dates = sorted(trend_data['daily_expenses'].keys())

        result = {
            'labels': [str(date) for date in sorted_dates],  # Ensure strings
            'dailyExpenses': [float(trend_data['daily_expenses'][date]) for date in sorted_dates],  # Ensure floats
            'movingAverages': [float(trend_data['moving_averages'].get(date, 0)) for date in sorted_dates],  # Ensure floats
            'totalSpending': float(trend_data['total_spending']),  # Ensure float
            'averageDaily': float(trend_data['average_daily'])  # Ensure float
        }

        return result

    except Exception as e:
        print(f"ERROR in get_daily_spending_data: {e}")
        import traceback
        print(f"ERROR traceback: {traceback.format_exc()}")

        # Return empty but valid data structure to prevent template errors
        return {
            'labels': [],
            'dailyExpenses': [],
            'movingAverages': [],
            'totalSpending': 0.0,
            'averageDaily': 0.0
        }


@login_required
def daily_spending_data_ajax(request):
    """
    AJAX endpoint to get daily spending data for different periods.
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        # Get the number of days from the request
        days = int(request.GET.get('days', 30))

        # Validate days parameter
        if days not in [7, 30, 60, 90]:
            return JsonResponse({'error': 'Invalid days parameter'}, status=400)

        # Resolve optional category filter
        category = None
        category_id = request.GET.get('category_id', '').strip()
        if category_id:
            try:
                category = Category.objects.get(id=int(category_id), type='expense')
            except (Category.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid category'}, status=400)

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
            'error': 'Failed to load daily spending data',
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
        return JsonResponse({'error': 'Invalid request'}, status=400)

    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Date parameter is required'}, status=400)

    try:
        # Parse date string (expected format: YYYY-MM-DD)
        from datetime import datetime
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Expected YYYY-MM-DD'}, status=400)

    try:
        from reports.repository.expense_repository import ExpenseRepository
        from decimal import Decimal

        expense_repo = ExpenseRepository()
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
                'category': expense['category__name'] or 'Sem Categoria',
                'payment_method': expense['payment_method__name'] or 'Sem Método',
                'created_at': expense['created_at'].strftime('%H:%M') if expense['created_at'] else '',
                'is_recurring': expense['reccurring_expense_id'] is not None,
                'is_installment': expense['installment_plan_id'] is not None,
            }
            expenses_list.append(expense_data)
            total_amount += expense['amount']

        categories = [
            {'category': row['category__name'] or 'Sem Categoria', 'total': float(row['total'])}
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
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


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
            return JsonResponse({'error': 'Invalid request - AJAX required'}, status=400)
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
                missing_params.append('year')
            if not request_month_name:
                missing_params.append('month')
            if not request_category:
                missing_params.append('category')

            return JsonResponse({
                'error': f'Missing required parameters: {", ".join(missing_params)}'
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
                'error': f'Invalid month name: {month_name}. Expected English month name (e.g., "January")'
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
            'category': expense_record['category__name'] or 'Uncategorized',
            'payment_method': expense_record['payment_method__name'] or 'N/A',
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
        expense_repository = ExpenseRepository()
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
            'error': f'Invalid data format: {str(validation_error)}'
        }, status=400)
    except Exception as unexpected_error:
        # Log the error for debugging (in production, use proper logging)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error fetching category expenses: {unexpected_error}', exc_info=True)

        return JsonResponse({
            'error': 'An unexpected error occurred while fetching expense details'
        }, status=500)


@login_required
def recurring_expense_list(request):
    """List all user's recurring expenses"""
    from utils.dates import get_all_months_tuples

    recurring_expense_service = RecurringExpenseService()
    recurring_expenses = recurring_expense_service.repository.get_all_recurring_expenses_by_user(request.user)

    # Calculate totals
    active_total = recurring_expense_service.repository.get_total_recurring_expenses_with_debit(request.user)
    inactive_total = recurring_expense_service.repository.get_total_inactive_recurring_expenses(request.user)
    total = active_total + inactive_total

    context = {
        'recurring_expenses': recurring_expenses,
        'active_total': active_total,
        'inactive_total': inactive_total,
        'total': total,
        'all_months': get_all_months_tuples(),
    }

    return render(request, 'reports/recurring_expense_list.html', context)


class RecurringExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for recurring expenses"""
    model = RecurringExpense
    form_class = RecurringExpenseForm
    template_name = 'reports/recurring_expense_update.html'
    success_url = '/recurring-expenses/'

    def get_form_kwargs(self):
        """Inject user into form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Add success message"""
        messages.success(self.request, "Recurring expense updated successfully.")
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def recurring_expense_delete(request, pk):
    """Delete recurring expense via AJAX"""
    try:
        recurring_expense_service = RecurringExpenseService()
        recurring_expense = recurring_expense_service.repository.get_recurring_expense_by_id(pk)

        # Verify if user owns the recurring expense
        if recurring_expense.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        description = recurring_expense.description
        recurring_expense_service.delete_recurring_expense(pk)

        return JsonResponse({
            'success': True,
            'message': f"Recurring expense '{description}' deleted successfully."
        })
    except RecurringExpense.DoesNotExist:
        return JsonResponse({'error': 'Recurring expense not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def recurring_expense_toggle(request, pk):
    """Toggle generate_debit field via AJAX"""
    try:
        recurring_expense_service = RecurringExpenseService()
        recurring_expense = recurring_expense_service.repository.get_recurring_expense_by_id(pk)

        # Verify ownership
        if recurring_expense.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        # Toggle the field
        updated_recurring_expense = recurring_expense_service.toggle_generate_debit(pk)

        return JsonResponse({
            'success': True,
            'generate_debit': updated_recurring_expense.generate_debit,
            'message': f"Recurring expense {'activated' if updated_recurring_expense.generate_debit else 'deactivated'}."
        })
    except RecurringExpense.DoesNotExist:
        return JsonResponse({'error': 'Recurring expense not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def recurring_expense_details_ajax(request):
    """AJAX endpoint to fetch expenses generated by recurring expense"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    recurring_expense_id = request.GET.get('id')
    if not recurring_expense_id:
        return JsonResponse({'error': 'ID parameter required'}, status=400)

    try:
        recurring_expense_service = RecurringExpenseService()
        data = recurring_expense_service.get_recurring_expense_with_expenses(int(recurring_expense_id))

        # Verify ownership
        if data['recurring_expense'].user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        # Format expenses for JSON response
        expenses_list = []
        for expense in data['expenses']:
            expenses_list.append({
                'id': expense.id,
                'date': expense.date.isoformat(),
                'description': expense.description,
                'amount': float(expense.amount),
                'category': expense.category.name if expense.category else 'N/A',
                'payment_method': expense.payment_method.name if expense.payment_method else 'N/A',
            })

        return JsonResponse({
            'recurring_expense': {
                'id': data['recurring_expense'].id,
                'description': data['recurring_expense'].description,
                'total_amount': float(data['recurring_expense'].total_amount),
                'generate_debit': data['recurring_expense'].generate_debit,
            },
            'expenses': expenses_list,
            'expense_count': data['expense_count'],
            'total_generated': float(data['total_generated']),
        })
    except RecurringExpense.DoesNotExist:
        return JsonResponse({'error': 'Recurring expense not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def process_recurring_expenses_ajax(request):
    """
    AJAX endpoint to process recurring expenses for a selected month/year.
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    try:
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
    except (TypeError, ValueError):
        return JsonResponse({
            'success': False,
            'error': 'Mês e ano inválidos'
        }, status=400)

    # Process expenses using service
    recurring_expense_service = RecurringExpenseService()
    result = recurring_expense_service.process_recurring_expenses_for_month(
        request.user, month, year
    )

    return JsonResponse(result)
