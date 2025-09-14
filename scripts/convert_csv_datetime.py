#!/usr/bin/env python3
import csv
import sys
from datetime import datetime
import argparse

def convert_pt_br_to_iso(date_str):
    """
    Convert Brazilian date format to ISO date format
    Expected input formats:
    - DD/MM/YYYY
    - DD/MM/YYYY HH:MM
    - DD/MM/YYYY HH:MM:SS
    """
    try:
        # Try different Brazilian datetime formats
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

        # If no format matches, return original value
        return date_str
    except Exception:
        return date_str

def convert_csv_datetime(input_path, output_path=None, date_column='date'):
    """
    Convert datetime column from PT-BR format to ISO format in CSV file
    """
    if output_path is None:
        output_path = input_path.replace('.csv', '_converted.csv')

    with open(input_path, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        if date_column not in fieldnames:
            print(f"Error: Column '{date_column}' not found in CSV file")
            print(f"Available columns: {', '.join(fieldnames)}")
            return False

        rows = []
        for row in reader:
            row[date_column] = convert_pt_br_to_iso(row[date_column])
            rows.append(row)

    with open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Successfully converted {len(rows)} rows")
    print(f"Output saved to: {output_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Convert CSV datetime column from PT-BR to ISO format')
    parser.add_argument('csv_path', help='Path to the CSV file')
    parser.add_argument('-o', '--output', help='Output file path (default: adds _converted suffix)')
    parser.add_argument('-c', '--column', default='date', help='Name of the date column (default: date)')

    args = parser.parse_args()

    try:
        convert_csv_datetime(args.csv_path, args.output, args.column)
    except FileNotFoundError:
        print(f"Error: File '{args.csv_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()