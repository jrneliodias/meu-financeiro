#!/usr/bin/env python3
import csv
import sys
from datetime import datetime
import argparse
import os

def convert_pt_br_to_iso(date_str):
    """
    Convert Brazilian date format to ISO date format
    """
    try:
        formats = [
            '%d/%m/%Y',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y %H:%M:%S'
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return date_str
    except Exception:
        return date_str

def process_csv(input_path, output_path=None, date_column='Data'):
    """
    Process CSV file:
    1. Convert date column from PT-BR to ISO format
    2. Replace " - " with "," in description (creating more columns)
    3. Remove columns 5 and 6+ (keep only first 4 columns)
    4. Remove ID column, keep only: date, amount, payment_method, description
    """
    if output_path is None:
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_processed.csv"

    # Step 1: Read and process the CSV
    with open(input_path, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        if date_column not in fieldnames:
            print(f"Error: Column '{date_column}' not found in CSV file")
            print(f"Available columns: {', '.join(fieldnames)}")
            return False

        processed_rows = []
        date_conversions = 0
        dash_replacements = 0

        for row in reader:
            processed_row = {}

            # Step 1: Convert date and map to new column name
            original_date = row['Data']
            converted_date = convert_pt_br_to_iso(original_date)
            if original_date != converted_date:
                date_conversions += 1
            processed_row['date'] = converted_date

            # Step 2: Map amount
            processed_row['amount'] = row['Valor']

            # Step 3: Process description - replace " - " with "," then split into columns
            full_description = row['Descrição']
            if ' - ' in full_description:
                # Replace " - " with "," to create more columns
                description_with_commas = full_description.replace(' - ', ',')
                # Split by comma to get all parts
                parts = description_with_commas.split(',')
                dash_replacements += 1
            else:
                parts = [full_description]

            # Map to columns (keeping only first 4: date, amount, payment_method, description)
            processed_row['payment_method'] = parts[0] if len(parts) > 0 else ''
            processed_row['description'] = parts[1] if len(parts) > 1 else ''
            # Parts 2, 3, 4, etc. (columns 5, 6, etc.) are discarded

            processed_rows.append(processed_row)

        # New fieldnames for output
        new_fieldnames = ['date', 'amount', 'payment_method', 'description']

    # Write processed CSV without using csv module to avoid escapes
    with open(output_path, 'w', encoding='utf-8') as outfile:
        # Write header
        outfile.write(','.join(new_fieldnames) + '\n')

        # Write rows
        for row in processed_rows:
            row_values = [str(row[col]) for col in new_fieldnames]
            outfile.write(','.join(row_values) + '\n')

    print(f"Successfully processed {len(processed_rows)} rows")
    print(f"Date conversions: {date_conversions}")
    print(f"Dash replacements: {dash_replacements}")
    print(f"Kept {len(new_fieldnames)} columns: {', '.join(new_fieldnames)}")
    print(f"Output saved to: {output_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Process CSV: convert dates, replace dashes, rename columns, remove ID')
    parser.add_argument('csv_path', help='Path to the CSV file')
    parser.add_argument('-o', '--output', help='Output file path (default: adds _processed suffix)')

    args = parser.parse_args()

    try:
        process_csv(args.csv_path, args.output)
    except FileNotFoundError:
        print(f"Error: File '{args.csv_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()