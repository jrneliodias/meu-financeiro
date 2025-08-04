import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from registers.services import CSVImportService
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Import expenses from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str,
                            help='Path to the CSV file')
        parser.add_argument('--separator', type=str, default=',',
                            help='CSV separator (default: ,)')
        parser.add_argument('--skip-header', action='store_true',
                            help='Skip the first row (header)')
        parser.add_argument('--user', type=str, default=None,
                            help='Username to import data for (default: first user)')
        parser.add_argument('--auto-create-categories', action='store_true', default=True,
                            help='Automatically create categories if they don\'t exist')
        parser.add_argument('--auto-create-payment-methods', action='store_true', default=True,
                            help='Automatically create payment methods if they don\'t exist')
        parser.add_argument('--preview', action='store_true',
                            help='Show preview only, don\'t import')

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file_path']
        separator = kwargs['separator']
        skip_header = kwargs['skip_header']
        username = kwargs['user']
        auto_create_categories = kwargs['auto_create_categories']
        auto_create_payment_methods = kwargs['auto_create_payment_methods']
        preview_only = kwargs['preview']

        # Check if file exists
        if not os.path.isabs(csv_file_path):
            csv_file_path = os.path.join(settings.BASE_DIR, csv_file_path)
        
        if not os.path.exists(csv_file_path):
            raise CommandError(f'File not found: {csv_file_path}')

        # Get user
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'User not found: {username}')
        else:
            user = User.objects.first()
            if not user:
                raise CommandError('No users found in database')

        # Initialize service
        service = CSVImportService()

        # Read and parse CSV
        self.stdout.write(f'Reading CSV file: {csv_file_path}')
        try:
            df = pd.read_csv(csv_file_path, sep=separator)
            
            if skip_header and not df.empty:
                df = df.iloc[1:].reset_index(drop=True)
            
            self.stdout.write(f'Found {len(df)} rows in CSV file')
            
        except Exception as e:
            raise CommandError(f'Error reading CSV file: {e}')

        # Validate structure
        is_valid, errors = service.validate_csv_structure(df)
        if not is_valid:
            for error in errors:
                self.stdout.write(self.style.ERROR(f'Validation error: {error}'))
            return

        # Clean data
        df, data_errors = service._clean_dataframe(df)
        for error in data_errors:
            self.stdout.write(self.style.WARNING(f'Data warning: {error}'))

        if preview_only:
            # Show preview
            preview_data = service.preview_data(df)
            self.stdout.write('\nPreview of data:')
            self.stdout.write('=' * 80)
            
            # Show column headers
            headers = list(df.columns)
            self.stdout.write(' | '.join(headers))
            self.stdout.write('-' * 80)
            
            # Show first 10 rows
            for i, row in df.head(10).iterrows():
                row_data = []
                for col in headers:
                    value = str(row.get(col, ''))
                    row_data.append(value[:20] + '...' if len(value) > 20 else value)
                self.stdout.write(' | '.join(row_data))
            
            self.stdout.write(f'\nTotal rows: {len(df)}')
            return

        # Import data
        self.stdout.write('Starting import...')
        result = service.import_data(
            df, user, auto_create_categories, auto_create_payment_methods
        )

        # Show results
        stats = result['stats']
        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed! {stats["imported"]} records imported successfully.'
            )
        )

        if result['errors']:
            self.stdout.write('\nErrors:')
            for error in result['errors']:
                self.stdout.write(self.style.ERROR(f'  - {error}'))

        if result['warnings']:
            self.stdout.write('\nWarnings:')
            for warning in result['warnings']:
                self.stdout.write(self.style.WARNING(f'  - {warning}'))

        # Summary
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'  - Total rows: {stats["total_rows"]}')
        self.stdout.write(f'  - Imported: {stats["imported"]}')
        self.stdout.write(f'  - Errors: {stats["errors"]}')
        self.stdout.write(f'  - Warnings: {stats["warnings"]}')
        self.stdout.write(f'  - Success rate: {stats["imported"] / stats["total_rows"] * 100:.1f}%') 