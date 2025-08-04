"""
CSV Import Component for handling CSV file imports with validation and processing
"""
from typing import Dict, List, Tuple, Optional
import pandas as pd
from django.core.files.uploadedfile import UploadedFile
from django.contrib.auth.models import User
from ..models import Category, PaymentMethod, Expense
import logging

logger = logging.getLogger(__name__)


class CSVImportComponent:
    """Component for handling CSV file imports with validation and error handling"""
    
    REQUIRED_COLUMNS = ['date', 'description', 'amount']
    OPTIONAL_COLUMNS = ['category', 'type', 'payment_method']
    
    def __init__(self):
        self.import_stats = {
            'total_rows': 0,
            'imported': 0,
            'errors': 0,
            'warnings': 0,
            'skipped': 0
        }
        self.error_log = []
        self.warning_log = []
    
    def validate_csv_structure(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate CSV structure and return validation status and errors"""
        errors = []
        
        # Check for required columns
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Check if dataframe is empty
        if df.empty:
            errors.append("CSV file is empty")
        
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
            errors.append(f"Error reading CSV file: {str(e)}")
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
                    errors.append(f"Invalid dates found in {len(invalid_dates)} rows")
            except Exception as e:
                errors.append(f"Error parsing dates: {str(e)}")
        
        # Validate amount column
        if 'amount' in df.columns:
            try:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                invalid_amounts = df[df['amount'].isna()]
                if not invalid_amounts.empty:
                    errors.append(f"Invalid amounts found in {len(invalid_amounts)} rows")
            except Exception as e:
                errors.append(f"Error parsing amounts: {str(e)}")
        
        # Set default values for optional columns
        if 'type' not in df.columns:
            df['type'] = 'expense'
        
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
        """Import data from DataFrame to database"""
        self.import_stats = {
            'total_rows': len(df),
            'imported': 0,
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
                    self._log_error(index, "Missing required fields")
                    continue
                
                # Handle category
                category_name = str(row.get('category', 'Outros')).strip()
                if auto_create_categories:
                    category, created = Category.objects.get_or_create(
                        name=category_name, 
                        type='expense',
                        defaults={'name': category_name, 'type': 'expense'}
                    )
                else:
                    try:
                        category = Category.objects.get(name=category_name, type='expense')
                    except Category.DoesNotExist:
                        self._log_warning(index, f"Category '{category_name}' not found, skipping")
                        continue
                
                # Handle payment method
                payment_method_name = str(row.get('payment_method', 'Crédito - Nubank')).strip()
                if auto_create_payment_methods:
                    payment_method, created = PaymentMethod.objects.get_or_create(
                        name=payment_method_name,
                        defaults={'name': payment_method_name, 'start_billing_day': 1}
                    )
                else:
                    try:
                        payment_method = PaymentMethod.objects.get(name=payment_method_name)
                    except PaymentMethod.DoesNotExist:
                        self._log_warning(index, f"Payment method '{payment_method_name}' not found, skipping")
                        continue
                
                # Create expense
                expense = Expense(
                    user=user,
                    description=str(row['description']).strip(),
                    amount=float(row['amount']),
                    date=row['date'].date() if hasattr(row['date'], 'date') else row['date'],
                    category=category,
                    payment_method=payment_method,
                )
                expense.save()
                
                self.import_stats['imported'] += 1
                
            except Exception as e:
                self._log_error(index, f"Error importing row: {str(e)}")
                logger.error(f"Import error at row {index}: {e}")
        
        return {
            'stats': self.import_stats,
            'errors': self.error_log,
            'warnings': self.warning_log
        }
    
    def _log_error(self, row_index: int, message: str):
        """Log an error for a specific row"""
        self.import_stats['errors'] += 1
        self.error_log.append(f"Row {row_index + 1}: {message}")
    
    def _log_warning(self, row_index: int, message: str):
        """Log a warning for a specific row"""
        self.import_stats['warnings'] += 1
        self.warning_log.append(f"Row {row_index + 1}: {message}")
    
    def get_import_summary(self) -> Dict:
        """Get a summary of the import operation"""
        return {
            'stats': self.import_stats,
            'success_rate': (self.import_stats['imported'] / self.import_stats['total_rows'] * 100) if self.import_stats['total_rows'] > 0 else 0,
            'errors': self.error_log,
            'warnings': self.warning_log
        } 