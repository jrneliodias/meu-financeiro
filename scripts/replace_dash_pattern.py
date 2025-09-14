#!/usr/bin/env python3
import csv
import sys
import argparse

def replace_dash_pattern(input_path, output_path=None, columns=None):
    """
    Replace " - " pattern with "," in specified CSV columns
    """
    if output_path is None:
        output_path = input_path.replace('.csv', '_replaced.csv')

    with open(input_path, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        if columns:
            # Validate specified columns exist
            invalid_columns = [col for col in columns if col not in fieldnames]
            if invalid_columns:
                print(f"Error: Columns not found: {', '.join(invalid_columns)}")
                print(f"Available columns: {', '.join(fieldnames)}")
                return False
            target_columns = columns
        else:
            # Apply to all columns if none specified
            target_columns = fieldnames

        rows = []
        replaced_count = 0

        for row in reader:
            for col in target_columns:
                if ' - ' in row[col]:
                    row[col] = row[col].replace(' - ', ',')
                    replaced_count += 1
            rows.append(row)

    with open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, quoting=csv.QUOTE_NONE, escapechar='\\')
        writer.writeheader()
        writer.writerows(rows)

    print(f"Successfully processed {len(rows)} rows")
    print(f"Replaced {replaced_count} occurrences of ' - ' with ','")
    print(f"Output saved to: {output_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Replace " - " pattern with "," in CSV columns')
    parser.add_argument('csv_path', help='Path to the CSV file')
    parser.add_argument('-o', '--output', help='Output file path (default: adds _replaced suffix)')
    parser.add_argument('-c', '--columns', nargs='+', help='Specific columns to process (default: all columns)')

    args = parser.parse_args()

    try:
        replace_dash_pattern(args.csv_path, args.output, args.columns)
    except FileNotFoundError:
        print(f"Error: File '{args.csv_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()