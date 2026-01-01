from datetime import datetime
import calendar


def get_current_date():
    """Get current year and month."""
    current = datetime.now()
    return current.year, current.month


def get_all_months():
    """Get list of all months."""
    return list(calendar.month_name)[1:]  # Skip empty first item


def get_all_months_tuples():
    """Get list of all months as tuples of (month_number, month_name).

    Returns:
        list: List of tuples [(1, 'January'), (2, 'February'), ..., (12, 'December')]
    """
    return [(month, calendar.month_name[month]) for month in range(1, 13)]
