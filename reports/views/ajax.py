"""Endpoint AJAX do gráfico de gasto diário."""
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
