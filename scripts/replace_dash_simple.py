#!/usr/bin/env python3
import sys
import argparse

def replace_dash_pattern(input_path, output_path=None):
    """
    Replace " - " pattern with "," in CSV file without adding quotes
    """
    if output_path is None:
        output_path = input_path.replace('.csv', '_replaced.csv')

    with open(input_path, 'r', encoding='utf-8') as infile:
        content = infile.read()

    # Replace " - " with ","
    new_content = content.replace(' - ', ',')

    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write(new_content)

    # Count replacements made
    replaced_count = content.count(' - ')

    print(f"Replaced {replaced_count} occurrences of ' - ' with ','")
    print(f"Output saved to: {output_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Replace " - " pattern with "," in CSV file')
    parser.add_argument('csv_path', help='Path to the CSV file')
    parser.add_argument('-o', '--output', help='Output file path (default: adds _replaced suffix)')

    args = parser.parse_args()

    try:
        replace_dash_pattern(args.csv_path, args.output)
    except FileNotFoundError:
        print(f"Error: File '{args.csv_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()