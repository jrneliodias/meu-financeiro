from datetime import datetime
import calendar


def get_current_date():
    """Get current year and month."""
    current = datetime.now()
    return current.year, current.month


def get_all_months():
    """Get list of all months."""
    return list(calendar.month_name)[1:]  # Skip empty first item
