"""
CSV Processor Service - Transformation-only CSV processing (no database operations)

This service transforms Nubank CSV exports into a standardized format ready for import.
Transformations include:
- Date conversion from PT-BR (DD/MM/YYYY) to ISO (YYYY-MM-DD) format
- Description parsing (split by " - " to extract payment_method and description)
- Column reorganization to standard format (date, amount, payment_method, description)

No database writes occur - this is a pure transformation service.
"""

import pandas as pd
import io
import csv
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import logging
from django.utils.translation import gettext as _, ngettext

logger = logging.getLogger(__name__)


class CSVProcessorService:
    """
    Service for processing and transforming CSV files from Nubank format to standardized format.

    Core responsibilities:
    - Auto-detect Nubank format (Data, Valor, Descrição columns)
    - Convert PT-BR dates to ISO format (DD/MM/YYYY → YYYY-MM-DD)
    - Parse descriptions (split by " - " separator)
    - Reorganize columns to standard format
    - Validate and clean data

    No database operations - pure transformation logic.
    """

    def __init__(self):
        """Initialize the CSV processor service"""
        self.required_columns = ['date', 'amount', 'payment_method', 'description']
        self.nubank_columns = ['Data', 'Valor', 'Descrição']

    def detect_format(self, df: pd.DataFrame) -> Optional[Dict[str, str]]:
        """
        Auto-detect Nubank CSV format by looking for expected column names.

        Args:
            df: DataFrame to analyze

        Returns:
            Dict mapping target columns to source columns, or None if not detected
            Example: {'date': 'Data', 'amount': 'Valor', 'description': 'Descrição'}
        """
        columns = df.columns.tolist()

        # Exact match for Nubank columns
        if all(col in columns for col in self.nubank_columns):
            return {
                'date': 'Data',
                'amount': 'Valor',
                'description': 'Descrição'
            }

        # Case-insensitive match
        columns_lower = {col.lower(): col for col in columns}

        if 'data' in columns_lower and 'valor' in columns_lower and 'descrição' in columns_lower:
            return {
                'date': columns_lower['data'],
                'amount': columns_lower['valor'],
                'description': columns_lower['descrição']
            }

        # Partial match (contains)
        date_col = next((col for col in columns if 'data' in col.lower()), None)
        valor_col = next((col for col in columns if 'valor' in col.lower()), None)
        desc_col = next((col for col in columns if 'desc' in col.lower()), None)

        if date_col and valor_col and desc_col:
            return {
                'date': date_col,
                'amount': valor_col,
                'description': desc_col
            }

        logger.warning(f"Could not auto-detect Nubank format. Available columns: {columns}")
        return None

    def convert_pt_br_to_iso(self, date_str: str) -> str:
        """
        Convert Brazilian date format to ISO date format.

        Supports multiple formats:
        - DD/MM/YYYY
        - DD/MM/YYYY HH:MM
        - DD/MM/YYYY HH:MM:SS

        Args:
            date_str: Date string in PT-BR format

        Returns:
            Date string in ISO format (YYYY-MM-DD) or original string if conversion fails
        """
        if pd.isna(date_str) or str(date_str).strip() == '':
            return ''

        try:
            formats = [
                '%d/%m/%Y',
                '%d/%m/%Y %H:%M',
                '%d/%m/%Y %H:%M:%S'
            ]

            date_str = str(date_str).strip()

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            # If no format matched, return original
            logger.warning(f"Could not convert date: {date_str}")
            return date_str

        except Exception as e:
            logger.error(f"Error converting date '{date_str}': {e}")
            return date_str

    def parse_description(self, desc: str) -> Tuple[str, str]:
        """
        Parse description by splitting on " - " separator.

        Examples:
        - "Uber - Trip" → payment_method="Uber", description="Trip"
        - "Pagamento recebido" → payment_method="Pagamento recebido", description=""
        - "Uber - Trip - Details" → payment_method="Uber", description="Trip - Details"

        Args:
            desc: Description string from CSV

        Returns:
            Tuple of (payment_method, description)
        """
        if pd.isna(desc) or str(desc).strip() == '':
            return '', ''

        desc_str = str(desc).strip()

        if ' - ' in desc_str:
            # Split only on first occurrence of " - "
            parts = desc_str.split(' - ', 1)
            payment_method = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else ''
            return payment_method, description
        else:
            # No separator, use entire string as payment_method
            return desc_str, ''

    def convert_date_column(self, df: pd.DataFrame, date_column: str) -> Tuple[pd.DataFrame, int, List[str]]:
        """
        Convert date column from PT-BR to ISO format.

        Args:
            df: DataFrame to process
            date_column: Name of the date column

        Returns:
            Tuple of (processed DataFrame, conversion count, error messages)
        """
        conversion_count = 0
        failed_rows = []
        errors = []

        for idx, row in df.iterrows():
            original = row[date_column]
            converted = self.convert_pt_br_to_iso(original)

            if converted != str(original):
                conversion_count += 1
            else:
                # Date wasn't converted - might already be ISO or invalid
                try:
                    # Try to validate as date
                    pd.to_datetime(converted)
                except:
                    failed_rows.append(idx + 2)  # +2 because idx is 0-based and header is row 1

            df.at[idx, date_column] = converted

        if failed_rows:
            # Show only first 10 failed rows to avoid cluttering
            failed_preview = ', '.join(map(str, failed_rows[:10]))
            if len(failed_rows) > 10:
                failed_preview += " " + ngettext(
                    "... and %(count)s more",
                    "... and %(count)s more",
                    len(failed_rows) - 10,
                ) % {'count': len(failed_rows) - 10}
            errors.append(ngettext(
                "Could not convert dates in %(count)s row: %(rows)s",
                "Could not convert dates in %(count)s rows: %(rows)s",
                len(failed_rows),
            ) % {
                'count': len(failed_rows),
                'rows': failed_preview,
            })

        logger.info(f"Converted {conversion_count} dates from PT-BR to ISO format")
        return df, conversion_count, errors

    def process_description_column(self, df: pd.DataFrame, desc_column: str) -> Tuple[pd.DataFrame, int]:
        """
        Process description column by parsing and splitting into payment_method and description.

        Args:
            df: DataFrame to process
            desc_column: Name of the description column

        Returns:
            Tuple of (processed DataFrame with new columns, split count)
        """
        split_count = 0
        payment_methods = []
        descriptions = []

        for idx, row in df.iterrows():
            desc = row[desc_column]
            payment_method, description = self.parse_description(desc)

            if ' - ' in str(desc):
                split_count += 1

            payment_methods.append(payment_method)
            descriptions.append(description)

        df['payment_method'] = payment_methods
        df['description'] = descriptions

        logger.info(f"Split {split_count} descriptions into payment_method and description")
        return df, split_count

    def reorganize_columns(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Reorganize DataFrame to have only the 4 standard columns in correct order.

        Args:
            df: DataFrame to reorganize
            column_mapping: Mapping of target columns to source columns

        Returns:
            DataFrame with only [date, amount, payment_method, description] columns
        """
        # Create new DataFrame with only required columns
        result_df = pd.DataFrame()

        result_df['date'] = df[column_mapping['date']]
        result_df['amount'] = df[column_mapping['amount']]
        result_df['payment_method'] = df['payment_method']
        result_df['description'] = df['description']

        return result_df

    def process_csv(self, df: pd.DataFrame, column_mapping: Optional[Dict[str, str]] = None) -> Tuple[pd.DataFrame, List[str]]:
        """
        Main orchestration method - process CSV through all transformations.

        Workflow:
        1. Auto-detect format or use manual mapping
        2. Convert date column to ISO format
        3. Parse description column into payment_method and description
        4. Reorganize to standard 4-column format

        Args:
            df: DataFrame to process
            column_mapping: Optional manual column mapping. If None, will auto-detect.

        Returns:
            Tuple of (processed DataFrame, list of error/warning messages)
        """
        errors = []
        warnings = []

        try:
            # Step 1: Determine column mapping
            if column_mapping is None:
                column_mapping = self.detect_format(df)
                if column_mapping is None:
                    available_cols = ', '.join(df.columns.tolist())
                    errors.append(_("Could not auto-detect Nubank format. Available columns: %(columns)s") % {
                        'columns': available_cols
                    })
                    return df, errors

            # Validate that mapped columns exist
            for target, source in column_mapping.items():
                if source not in df.columns:
                    errors.append(_("Column '%(column)s' not found in CSV. Available: %(available)s") % {
                        'column': source,
                        'available': ', '.join(df.columns.tolist()),
                    })
                    return df, errors

            # Step 2: Convert dates
            df_copy = df.copy()
            df_copy, conversion_count, date_errors = self.convert_date_column(
                df_copy,
                column_mapping['date']
            )
            warnings.extend(date_errors)

            # Step 3: Process descriptions
            df_copy, split_count = self.process_description_column(
                df_copy,
                column_mapping['description']
            )

            # Step 4: Reorganize columns
            result_df = self.reorganize_columns(df_copy, column_mapping)

            # Add success stats as info messages
            stats = [
                ngettext(
                    "Successfully processed %(count)s row",
                    "Successfully processed %(count)s rows",
                    len(result_df),
                ) % {'count': len(result_df)},
                ngettext(
                    "Converted %(count)s date to ISO format",
                    "Converted %(count)s dates to ISO format",
                    conversion_count,
                ) % {'count': conversion_count},
                ngettext(
                    "Parsed %(count)s description into payment method and description",
                    "Parsed %(count)s descriptions into payment method and description",
                    split_count,
                ) % {'count': split_count}
            ]

            logger.info(' | '.join(stats))

            return result_df, warnings

        except Exception as e:
            error_msg = _("Error processing CSV: %(error)s") % {'error': str(e)}
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            return df, errors

    def dataframe_to_csv_string(self, df: pd.DataFrame) -> str:
        """
        Convert DataFrame to CSV string for download or clipboard.

        Uses proper CSV quoting to handle special characters correctly.

        Args:
            df: DataFrame to convert

        Returns:
            CSV string representation
        """
        try:
            # Use StringIO to capture CSV output
            output = io.StringIO()
            df.to_csv(
                output,
                index=False,
                quoting=csv.QUOTE_MINIMAL,
                lineterminator='\n'
            )
            csv_string = output.getvalue()
            output.close()

            return csv_string

        except Exception as e:
            logger.error(f"Error converting DataFrame to CSV string: {e}", exc_info=True)
            # Fallback: simple join
            lines = [','.join(df.columns)]
            for _, row in df.iterrows():
                values = [str(row[col]) for col in df.columns]
                lines.append(','.join(values))
            return '\n'.join(lines)

    def parse_csv_file(self, uploaded_file, separator: str = ',') -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Parse uploaded CSV file into DataFrame.

        Args:
            uploaded_file: Django UploadedFile object
            separator: CSV separator character

        Returns:
            Tuple of (DataFrame or None if error, list of error messages)
        """
        try:
            df = pd.read_csv(uploaded_file, sep=separator)
            return df, []
        except Exception as e:
            error_msg = _("Error reading CSV file: %(error)s") % {'error': str(e)}
            logger.error(error_msg, exc_info=True)
            return None, [error_msg]

    def parse_csv_from_string(self, csv_string: str, separator: str = ',') -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Parse CSV string into DataFrame.

        Args:
            csv_string: CSV content as string
            separator: CSV separator character

        Returns:
            Tuple of (DataFrame or None if error, list of error messages)
        """
        try:
            df = pd.read_csv(io.StringIO(csv_string), sep=separator)
            return df, []
        except Exception as e:
            error_msg = _("Error reading CSV text: %(error)s") % {'error': str(e)}
            logger.error(error_msg, exc_info=True)
            return None, [error_msg]
