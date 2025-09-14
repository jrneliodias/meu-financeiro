#!/usr/bin/env python3
import csv
import sys
import argparse

def remove_columns_from_index(input_path, output_path=None, start_index=5):
    """
    Remove columns starting from specified index (0-based)
    Default removes from 6th column onwards (index 5)
    """
    if output_path is None:
        output_path = input_path.replace('.csv', '_trimmed.csv')

    with open(input_path, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)

        rows = []
        for row in reader:
            # Keep only columns up to start_index
            trimmed_row = row[:start_index]
            rows.append(trimmed_row)

    with open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile, quoting=csv.QUOTE_NONE, escapechar='\\')
        writer.writerows(rows)

    original_columns = len(rows[0]) + len(rows[0][start_index:]) if rows else 0
    remaining_columns = len(rows[0]) if rows else 0
    removed_columns = original_columns - remaining_columns

    print(f"Successfully processed {len(rows)} rows")
    print(f"Removed {removed_columns} columns (kept first {remaining_columns} columns)")
    print(f"Output saved to: {output_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Remove columns from CSV starting at specified index')
    parser.add_argument('csv_path', help='Path to the CSV file')
    parser.add_argument('-o', '--output', help='Output file path (default: adds _trimmed suffix)')
    parser.add_argument('-s', '--start', type=int, default=5, help='Index to start removing columns from (0-based, default: 5 for 6th column)')

    args = parser.parse_args()

    try:
        remove_columns_from_index(args.csv_path, args.output, args.start)
    except FileNotFoundError:
        print(f"Error: File '{args.csv_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()