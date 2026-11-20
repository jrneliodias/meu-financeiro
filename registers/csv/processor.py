"""Turn a Nubank CSV export into the standard import format (date, amount, payment_method, description).

Dates go from DD/MM/YYYY to ISO; "Uber - Trip" descriptions split into payment_method "Uber"
and description "Trip". Nothing is written to the database.
"""
import csv
from datetime import datetime

import pandas as pd
from django.utils.translation import gettext as _, ngettext

NUBANK_COLUMNS = {'date': 'Data', 'amount': 'Valor', 'description': 'Descrição'}
PT_BR_DATE_FORMATS = ('%d/%m/%Y', '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S')
FAILED_ROWS_SHOWN = 10


def detect_columns(df):
    """{'date', 'amount', 'description'} → source column, by Nubank's names (exact, any case, then partial)."""
    columns = df.columns.tolist()
    if all(name in columns for name in NUBANK_COLUMNS.values()):
        return dict(NUBANK_COLUMNS)
    by_lower = {column.lower(): column for column in columns}
    if all(name.lower() in by_lower for name in NUBANK_COLUMNS.values()):
        return {target: by_lower[name.lower()] for target, name in NUBANK_COLUMNS.items()}
    partial = {
        'date': next((c for c in columns if 'data' in c.lower()), None),
        'amount': next((c for c in columns if 'valor' in c.lower()), None),
        'description': next((c for c in columns if 'desc' in c.lower()), None),
    }
    return partial if all(partial.values()) else None


def to_iso_date(value):
    """DD/MM/YYYY[ HH:MM[:SS]] → YYYY-MM-DD; anything else comes back unchanged ('' for blanks)."""
    if pd.isna(value) or str(value).strip() == '':
        return ''
    text = str(value).strip()
    for date_format in PT_BR_DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return text


def split_description(value):
    """'Uber - Trip - X' → ('Uber', 'Trip - X'); no ' - ' → (whole text, '')."""
    if pd.isna(value) or str(value).strip() == '':
        return '', ''
    payment_method, _sep, description = str(value).strip().partition(' - ')
    return payment_method.strip(), description.strip()


def process(df, columns):
    """(standard DataFrame, warnings) or (None, errors) when the mapped columns are missing."""
    missing = [source for source in columns.values() if source not in df.columns]
    if missing:
        return None, [_("Column '%(column)s' not found in CSV. Available: %(available)s") % {
            'column': missing[0], 'available': ', '.join(df.columns.tolist()),
        }]

    dates = df[columns['date']].map(to_iso_date)
    failed_rows = [index + 2 for index, (original, converted) in enumerate(zip(df[columns['date']], dates))
                   if converted == str(original) and pd.isna(pd.to_datetime(converted, errors='coerce'))]
    warnings = []
    if failed_rows:
        shown = ', '.join(map(str, failed_rows[:FAILED_ROWS_SHOWN]))
        hidden = len(failed_rows) - FAILED_ROWS_SHOWN
        if hidden > 0:
            shown += " " + ngettext("... and %(count)s more", "... and %(count)s more", hidden) % {'count': hidden}
        warnings.append(ngettext(
            "Could not convert dates in %(count)s row: %(rows)s",
            "Could not convert dates in %(count)s rows: %(rows)s",
            len(failed_rows),
        ) % {'count': len(failed_rows), 'rows': shown})

    split = df[columns['description']].map(split_description)
    return pd.DataFrame({
        'date': dates.values,
        'amount': df[columns['amount']].values,
        'payment_method': [payment_method for payment_method, _description in split],
        'description': [description for _payment_method, description in split],
    }), warnings


def to_csv_string(df):
    return df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
