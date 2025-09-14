#!/usr/bin/env python3
"""
Test script for CSV import functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance.settings')
django.setup()

from registers.services import CSVImportService
from django.contrib.auth.models import User
import pandas as pd
import io

def test_csv_import():
    """Test the CSV import functionality"""
    
    # Create test CSV data
    csv_data = """date,description,amount,category,type,payment_method
2025-01-15,Test Grocery,45.67,Supermercado,expense,Crédito - Nubank
2025-01-16,Test Uber,12.50,Uber,expense,Crédito - Nubank
2025-01-17,Test Restaurant,25.00,Jantar,expense,Crédito - Nubank"""
    
    # Create a file-like object
    csv_file = io.StringIO(csv_data)
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    
    # Initialize the service
    service = CSVImportService()
    
    # Test parsing
    print("Testing CSV parsing...")
    df, errors = service.parse_csv_file_from_string(csv_data)
    
    if df is None:
        print("❌ CSV parsing failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ CSV parsing successful")
    print(f"  - Found {len(df)} rows")
    print(f"  - Columns: {list(df.columns)}")
    
    # Test preview
    print("\nTesting preview...")
    preview_data = service.preview_data(df)
    print(f"✅ Preview generated with {len(preview_data['sample_data'])} sample records")
    
    # Test import
    print("\nTesting import...")
    result = service.import_data(df, user, auto_create_categories=True, auto_create_payment_methods=True)
    
    stats = result['stats']
    print(f"✅ Import completed:")
    print(f"  - Total rows: {stats['total_rows']}")
    print(f"  - Imported: {stats['imported']}")
    print(f"  - Errors: {stats['errors']}")
    print(f"  - Warnings: {stats['warnings']}")
    
    if result['errors']:
        print("  Errors:")
        for error in result['errors']:
            print(f"    - {error}")
    
    if result['warnings']:
        print("  Warnings:")
        for warning in result['warnings']:
            print(f"    - {warning}")
    
    return True

if __name__ == '__main__':
    print("Testing CSV Import Functionality")
    print("=" * 40)
    
    success = test_csv_import()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1) 