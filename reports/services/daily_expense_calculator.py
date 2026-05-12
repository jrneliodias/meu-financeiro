from datetime import date, timedelta
from typing import Dict, List
from reports.utils import debug_to_json
import calendar

class DailyExpenseCalculator:
    """
    Service class responsible for calculating daily expense aggregations.
    
    Design Principles:
    1. Single Responsibility: Focuses only on daily calculations
    2. Dependency Injection: Receives repository as dependency
    3. Immutable Operations: Doesn't modify input data
    4. Comprehensive Logging: Uses existing debug patterns
    """
    
    def __init__(self, expense_repository, year: int = None, month: int = None):
        self.expense_repository = expense_repository
        self.year = year or date.today().year
        self.month = month or date.today().month
    
    def calculate_daily_expenses_for_period(self, start_date: date, end_date: date, 
                                          payment_method=None, category=None) -> Dict[str, float]:
        """
        Calculate daily expenses for a specific period with optional filters.
        
        Args:
            start_date: Period start date
            end_date: Period end date  
            payment_method: Optional payment method filter
            category: Optional category filter
            
        Returns:
            Dictionary with date strings as keys and expense totals as values
        """
        # Create a complete date range with zero values first
        daily_expenses = self._initialize_date_range(start_date, end_date)
        
        try:
            # Build the query with filters
            expenses_query = self.expense_repository.get_daily_expenses_in_period(
                start_date, end_date, payment_method, category
            )
            
            # Fill in actual expense data
            for expense in expenses_query:
                # Fixed: The repository now returns 'date' directly
                expense_date = expense.get('date')
                total_amount = expense.get('total_amount', 0)
                
                if expense_date and total_amount is not None:
                    date_str = expense_date.strftime('%Y-%m-%d')
                    daily_expenses[date_str] = float(total_amount)
            
        except Exception as e:
            # Log the error for debugging but don't crash the application
            self._debug_query_error(start_date, end_date, e, payment_method, category)
            # daily_expenses already has zero values, so we can continue
        
        # Debug logging for transparency
        self._debug_daily_calculation(start_date, end_date, daily_expenses, 
                                    payment_method, category)
        
        return daily_expenses
    
    def calculate_daily_expenses_for_month(self, year: int = None, month: int = None) -> Dict[str, float]:
        """
        Calculate daily expenses for a specific month.
        
        Why separate method? Monthly calculations are common and this provides
        a convenient interface while maintaining the flexibility of the period method.
        """
        year = year or self.year
        month = month or self.month
        
        # Get first and last day of month
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        
        return self.calculate_daily_expenses_for_period(start_date, end_date)
    
    def get_daily_spending_trends(self, days: int = 30, category=None) -> Dict[str, any]:
        """
        Calculate spending trends for the last N days.

        Returns comprehensive trend data including:
        - Daily totals
        - Moving averages
        - Trend indicators
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        daily_expenses = self.calculate_daily_expenses_for_period(start_date, end_date, category=category)
        
        # Calculate moving average (7-day window)
        moving_averages = self._calculate_moving_average(daily_expenses, window=7)
        
        # Calculate trend indicators
        total_spending = sum(daily_expenses.values())
        average_daily = total_spending / days if days > 0 else 0
        
        trend_data = {
            'daily_expenses': daily_expenses,
            'moving_averages': moving_averages,
            'total_spending': total_spending,
            'average_daily': average_daily,
            'period_days': days
        }
        
        self._debug_trend_calculation(trend_data)
        return trend_data
    
    def _initialize_date_range(self, start_date: date, end_date: date) -> Dict[str, float]:
        """Initialize all dates in range with zero values."""
        daily_expenses = {}
        current_date = start_date
        
        while current_date <= end_date:
            daily_expenses[current_date.strftime('%Y-%m-%d')] = 0.0
            current_date += timedelta(days=1)
            
        return daily_expenses
    
    def _calculate_moving_average(self, daily_data: Dict[str, float], window: int = 7) -> Dict[str, float]:
        """Calculate moving average for smoothing daily variations."""
        sorted_dates = sorted(daily_data.keys())
        moving_averages = {}
        
        for i, date_str in enumerate(sorted_dates):
            if i >= window - 1:
                # Get the last 'window' values
                window_values = [daily_data[sorted_dates[j]] for j in range(i - window + 1, i + 1)]
                moving_averages[date_str] = sum(window_values) / window
            else:
                # For early dates, use available data
                window_values = [daily_data[sorted_dates[j]] for j in range(0, i + 1)]
                moving_averages[date_str] = sum(window_values) / len(window_values) if window_values else 0
        
        return moving_averages
    
    def _debug_daily_calculation(self, start_date: date, end_date: date, 
                                daily_expenses: Dict[str, float], payment_method, category):
        """Debug logging following existing patterns."""
        try:
            debug_to_json(
                data={
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'payment_method': payment_method.name if payment_method else None,
                    'category': category.name if category else None,
                    'total_days': len(daily_expenses),
                    'total_amount': sum(daily_expenses.values()),
                    'non_zero_days': len([v for v in daily_expenses.values() if v > 0])
                },
                filename_prefix='daily_expense_calculation'
            )
        except Exception as e:
            print(f"Debug logging failed: {e}")
    
    def _debug_trend_calculation(self, trend_data: Dict[str, any]):
        """Debug trend calculations."""
        try:
            expenses_values = list(trend_data['daily_expenses'].values())
            debug_to_json(
                data={
                    'total_spending': trend_data['total_spending'],
                    'average_daily': trend_data['average_daily'],
                    'period_days': trend_data['period_days'],
                    'highest_day': max(expenses_values) if expenses_values else 0,
                    'lowest_day': min(expenses_values) if expenses_values else 0
                },
                filename_prefix='daily_trend_calculation'
            )
        except Exception as e:
            print(f"Debug trend logging failed: {e}")
    
    def _debug_query_error(self, start_date: date, end_date: date, error: Exception, 
                          payment_method=None, category=None):
        """Debug query errors to help with troubleshooting."""
        try:
            debug_to_json(
                data={
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'payment_method': payment_method.name if payment_method else None,
                    'category': category.name if category else None,
                },
                filename_prefix='daily_expense_query_error'
            )
        except:
            # If debug logging fails, at least print to console
            print(f"Daily expense query error: {error}")