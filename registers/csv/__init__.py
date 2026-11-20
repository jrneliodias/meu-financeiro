import pandas as pd
from django.utils.translation import gettext as _


def read(source, separator=','):
    """(DataFrame, []) for a file, path or text buffer, or (None, [error]) when pandas can't read it."""
    try:
        return pd.read_csv(source, sep=separator), []
    except Exception as e:  # pandas raises many types for malformed input; the user gets the message
        return None, [_("Error reading CSV file: %(error)s") % {'error': str(e)}]


def records(df):
    """Rows as dicts with None for blanks (NaN/NaT), safe for templates and JSON."""
    return df.astype(object).where(df.notna(), None).to_dict('records')
