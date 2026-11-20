"""Import a standard CSV (date, description, amount[, category, type, payment_method]) as expenses and incomes.

A row is an expense or an income by its `type` column; without one, by the sign of the amount
(negative = expense, positive = income). Amounts are stored as absolute values.
"""
import logging

import pandas as pd
from django.utils.translation import gettext as _, ngettext

from ..models import Category, Expense, Income, PaymentMethod
from . import read, records

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ['date', 'description', 'amount']
DEFAULT_CATEGORY = 'Outros'
DEFAULT_PAYMENT_METHOD = 'Crédito - Nubank'
PREVIEW_ROWS = 10


class RowError(Exception):
    pass


def read_csv(source, separator=','):
    """(DataFrame, warnings) for a file, path or text buffer; (None, errors) when it can't be imported."""
    df, errors = read(source, separator)
    if df is None:
        return None, errors

    df = df.dropna(how='all')
    errors = []
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        errors.append(_("Missing required columns: %(columns)s") % {'columns': ', '.join(missing)})
    if df.empty:
        errors.append(_("CSV file is empty"))
    if errors:
        return None, errors

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    warnings = []
    if invalid := int(df['date'].isna().sum()):
        warnings.append(ngettext("Invalid date found in %(count)s row", "Invalid dates found in %(count)s rows",
                                 invalid) % {'count': invalid})
    if invalid := int(df['amount'].isna().sum()):
        warnings.append(ngettext("Invalid amount found in %(count)s row", "Invalid amounts found in %(count)s rows",
                                 invalid) % {'count': invalid})
    if 'category' not in df.columns:
        df['category'] = DEFAULT_CATEGORY
    if 'payment_method' not in df.columns:
        df['payment_method'] = DEFAULT_PAYMENT_METHOD
    return df, warnings


def preview(df):
    return {
        'total_rows': len(df),
        'columns': list(df.columns),
        'sample_data': records(df.head(PREVIEW_ROWS)),
    }



def import_rows(df, user, auto_create_categories=True, auto_create_payment_methods=True):
    """Create one Expense or Income per row. Returns {'stats': {...}, 'errors': ["Row n: …"]}."""
    stats = {'total_rows': len(df), 'imported': 0, 'imported_expenses': 0, 'imported_incomes': 0, 'errors': 0}
    errors = []
    for index, row in df.iterrows():
        try:
            record = _create_record(user, row, auto_create_categories, auto_create_payment_methods)
        except Exception as e:  # one bad row must not stop the import; it is reported back
            if not isinstance(e, RowError):
                logger.exception('CSV import failed on row %s', index + 1)
            message = str(e) if isinstance(e, RowError) else _("Error importing row: %(error)s") % {'error': e}
            stats['errors'] += 1
            errors.append(_("Row %(row)s: %(message)s") % {'row': index + 1, 'message': message})
            continue
        stats['imported'] += 1
        stats['imported_expenses' if isinstance(record, Expense) else 'imported_incomes'] += 1
    return {'stats': stats, 'errors': errors}


def _text(row, column, default=''):
    value = row.get(column)
    return default if value is None or pd.isna(value) else str(value).strip()


def _record_type(row):
    explicit = _text(row, 'type').lower()
    if explicit in ('expense', 'income'):
        return explicit
    if row['amount'] < 0:
        return 'expense'
    if row['amount'] > 0:
        return 'income'
    return None


def _category(name, type, auto_create):
    if auto_create:
        return Category.objects.get_or_create(name=name, type=type)[0]
    category = Category.objects.filter(name=name, type=type).first()
    if category is None:
        raise RowError(_("Category '%(category)s' of type '%(type)s' not found") % {'category': name, 'type': type})
    return category


def _payment_method(name, auto_create):
    if auto_create:
        return PaymentMethod.objects.get_or_create(name=name, defaults={'start_billing_day': 1})[0]
    payment_method = PaymentMethod.objects.filter(name=name).first()
    if payment_method is None:
        raise RowError(_("Payment method '%(payment_method)s' not found") % {'payment_method': name})
    return payment_method


def _create_record(user, row, auto_create_categories, auto_create_payment_methods):
    if pd.isna(row['date']) or pd.isna(row['description']) or pd.isna(row['amount']):
        raise RowError(_("Missing required fields"))
    record_type = _record_type(row)
    if record_type is None:
        raise RowError(_("Amount is zero or invalid"))
    fields = {
        'user': user,
        'description': _text(row, 'description'),
        'amount': abs(float(row['amount'])),
        'date': row['date'].date(),
        'category': _category(_text(row, 'category', DEFAULT_CATEGORY), record_type, auto_create_categories),
    }
    if record_type == 'income':
        return Income.objects.create(**fields)
    payment_method = _payment_method(_text(row, 'payment_method', DEFAULT_PAYMENT_METHOD), auto_create_payment_methods)
    return Expense.objects.create(payment_method=payment_method, **fields)
