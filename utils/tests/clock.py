"""Freeze Django's clock in tests: everything that calls timezone.now() or localdate() sees the frozen moment."""
from datetime import datetime
from unittest.mock import patch

from django.utils import timezone


def at(moment):
    """Make the aware datetime `moment` now."""
    return patch('django.utils.timezone.now', return_value=moment)


def today_is(day):
    """Make noon of `day`, in the project's time zone, now."""
    return at(timezone.make_aware(datetime(day.year, day.month, day.day, 12)))
