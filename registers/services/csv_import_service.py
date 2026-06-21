import pandas as pd
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from typing import Dict, List, Tuple, Optional
import logging
import io
from django.utils.translation import gettext as _, ngettext

from ..models import Expense, Income, Category, PaymentMethod
from .csv_record_strategies import RecordStrategyFactory

logger = logging.getLogger(__name__)


class CSVImportService:
    """
    Service for handling CSV file imports with validation and error handling.

    SOLID Principles Applied:
    - Single Responsibility: Handles CSV parsing, validation, and orchestration
    - Open/Closed: Extensible via strategy pattern without modification
    - Dependency Inversion: Depends on RecordStrategyFactory abstraction

    The service now supports both Expense and Income creation based on:
    1. Explicit 'type' column in CSV (takes precedence)
    2. Sign of amount: negative = expense, positive = income
    """

    REQUIRED_COLUMNS = ['date', 'description', 'amount']
    OPTIONAL_COLUMNS = ['category', 'type', 'payment_method']

    def __init__(self):
        self.import_stats = {
            'total_rows': 0,
            'imported': 0,
            'imported_expenses': 0,
            'imported_incomes': 0,
            'errors': 0,
            'warnings': 0,
            'skipped': 0
        }
        self.error_log = []
        self.warning_log = []
        self.strategy_factory = RecordStrategyFactory()
    
    def validate_csv_structure(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate CSV structure and return validation status and errors"""
        errors = []
        
        # Check for required columns
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            errors.append(_("Missing required columns: %(columns)s") % {
                'columns': ', '.join(missing_columns)
            })
        
        # Check if dataframe is empty
        if df.empty:
            errors.append(_("CSV file is empty"))
        
        return len(errors) == 0, errors
    
    def parse_csv_file(self, uploaded_file: UploadedFile, separator: str = ',', 
                      skip_header: bool = True) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """Parse uploaded CSV file and return DataFrame with errors"""
        errors = []
        
        try:
            # Read CSV with specified separator
            df = pd.read_csv(uploaded_file, sep=separator)
            
            # Skip header if requested
            if skip_header and not df.empty:
                df = df.iloc[1:].reset_index(drop=True)
            
            # Validate structure
            is_valid, structure_errors = self.validate_csv_structure(df)
            if not is_valid:
                errors.extend(structure_errors)
                return None, errors
            
            # Clean and validate data
            df, data_errors = self._clean_dataframe(df)
            errors.extend(data_errors)
            
            return df, errors
            
        except Exception as e:
            errors.append(_("Error reading CSV file: %(error)s") % {'error': str(e)})
            logger.error(f"CSV parsing error: {e}")
            return None, errors
    
    def parse_csv_file_from_string(self, csv_string: str, separator: str = ',', 
                                 skip_header: bool = True) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """Parse CSV string and return DataFrame with errors (for testing)"""
        errors = []
        
        try:
            # Read CSV from string
            df = pd.read_csv(io.StringIO(csv_string), sep=separator)
            
            # Skip header if requested
            if skip_header and not df.empty:
                df = df.iloc[1:].reset_index(drop=True)
            
            # Validate structure
            is_valid, structure_errors = self.validate_csv_structure(df)
            if not is_valid:
                errors.extend(structure_errors)
                return None, errors
            
            # Clean and validate data
            df, data_errors = self._clean_dataframe(df)
            errors.extend(data_errors)
            
            return df, errors
            
        except Exception as e:
            errors.append(_("Error reading CSV string: %(error)s") % {'error': str(e)})
            logger.error(f"CSV parsing error: {e}")
            return None, errors
    
    def _clean_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Clean and validate DataFrame data"""
        errors = []
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Validate date column
        if 'date' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                invalid_dates = df[df['date'].isna()]
                if not invalid_dates.empty:
                    errors.append(ngettext(
                        "Invalid date found in %(count)s row",
                        "Invalid dates found in %(count)s rows",
                        len(invalid_dates),
                    ) % {'count': len(invalid_dates)})
            except Exception as e:
                errors.append(_("Error parsing dates: %(error)s") % {'error': str(e)})
        
        # Validate amount column
        if 'amount' in df.columns:
            try:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                invalid_amounts = df[df['amount'].isna()]
                if not invalid_amounts.empty:
                    errors.append(ngettext(
                        "Invalid amount found in %(count)s row",
                        "Invalid amounts found in %(count)s rows",
                        len(invalid_amounts),
                    ) % {'count': len(invalid_amounts)})
            except Exception as e:
                errors.append(_("Error parsing amounts: %(error)s") % {'error': str(e)})
        
        # Set default values for optional columns
        if 'category' not in df.columns:
            df['category'] = 'Outros'
        
        if 'payment_method' not in df.columns:
            df['payment_method'] = 'Crédito - Nubank'
        
        return df, errors
    
    def preview_data(self, df: pd.DataFrame, limit: int = 10) -> Dict:
        """Generate preview data for the import"""
        preview_df = df.head(limit)
        
        return {
            'preview_data': preview_df.to_dict('records'),
            'total_rows': len(df),
            'columns': list(df.columns),
            'sample_data': preview_df.to_dict('records')
        }
    
    def import_data(self, df: pd.DataFrame, user: User,
                   auto_create_categories: bool = True,
                   auto_create_payment_methods: bool = True) -> Dict:
        """
        Import data from DataFrame to database using strategy pattern.

        This method now supports both Expense and Income creation:
        - Uses RecordStrategyFactory to determine the appropriate record type
        - Negative amounts → Expense records
        - Positive amounts → Income records
        - Explicit 'type' column → Takes precedence over amount sign

        Args:
            df: DataFrame containing CSV data
            user: User who owns the records
            auto_create_categories: Whether to auto-create missing categories
            auto_create_payment_methods: Whether to auto-create missing payment methods

        Returns:
            Dictionary with import statistics, errors, and warnings
        """
        self.import_stats = {
            'total_rows': len(df),
            'imported': 0,
            'imported_expenses': 0,
            'imported_incomes': 0,
            'errors': 0,
            'warnings': 0,
            'skipped': 0
        }
        self.error_log = []
        self.warning_log = []

        for index, row in df.iterrows():
            try:
                # Validate required fields
                if pd.isna(row['date']) or pd.isna(row['description']) or pd.isna(row['amount']):
                    self._log_error(index, _("Missing required fields"))
                    continue

                # Convert row to dictionary for strategy pattern
                row_data = row.to_dict()

                # Get appropriate strategy for this row
                strategy = self.strategy_factory.get_strategy(row_data)

                if strategy is None:
                    self._log_error(index, _("No strategy found to handle this row (amount is zero or invalid)"))
                    continue

                # Create record using the selected strategy
                record, error = strategy.create_record(
                    user=user,
                    row_data=row_data,
                    auto_create_categories=auto_create_categories,
                    auto_create_payment_methods=auto_create_payment_methods
                )

                if error:
                    self._log_error(index, error)
                    continue

                # Update statistics based on record type
                self.import_stats['imported'] += 1
                if isinstance(record, Expense):
                    self.import_stats['imported_expenses'] += 1
                elif isinstance(record, Income):
                    self.import_stats['imported_incomes'] += 1

            except Exception as e:
                self._log_error(index, _("Error importing row: %(error)s") % {'error': str(e)})
                logger.error(f"Import error at row {index}: {e}")

        return {
            'stats': self.import_stats,
            'errors': self.error_log,
            'warnings': self.warning_log
        }
    
    def _log_error(self, row_index: int, message: str):
        """Log an error for a specific row"""
        self.import_stats['errors'] += 1
        self.error_log.append(_("Row %(row)s: %(message)s") % {
            'row': row_index + 1,
            'message': message,
        })
    
    def _log_warning(self, row_index: int, message: str):
        """Log a warning for a specific row"""
        self.import_stats['warnings'] += 1
        self.warning_log.append(_("Row %(row)s: %(message)s") % {
            'row': row_index + 1,
            'message': message,
        })
    
    def get_import_summary(self) -> Dict:
        """Get a summary of the import operation"""
        return {
            'stats': self.import_stats,
            'success_rate': (self.import_stats['imported'] / self.import_stats['total_rows'] * 100) if self.import_stats['total_rows'] > 0 else 0,
            'errors': self.error_log,
            'warnings': self.warning_log
        }
