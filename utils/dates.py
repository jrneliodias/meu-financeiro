import calendar
from datetime import date

from django.utils.timezone import localdate

YEAR_RANGE = (2000, 2100)


def month_end(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


def parse_month_year(params, required=False):
    """(year, month) from request params; missing ones default to today's unless `required`.

    Raises ValueError for missing required values, non-numbers, months outside 1-12 and years outside YEAR_RANGE.
    """
    if required and not (params.get('month') and params.get('year')):
        raise ValueError('month and year are required')
    today = localdate()
    month = int(params.get('month') or today.month)
    year = int(params.get('year') or today.year)
    if not (1 <= month <= 12 and YEAR_RANGE[0] <= year <= YEAR_RANGE[1]):
        raise ValueError(f'invalid month/year: {month}/{year}')
    return year, month
