#!/usr/bin/env python3
"""
CSV Parsing Tool for W3BHub WhatsApp Automation System

This tool helps diagnose CSV parsing issues by:
- Checking file encoding
- Detecting delimiters
- Validating headers
- Showing sample data
"""

import csv
import sys
import argparse
from pathlib import Path

def detect_encoding(filepath):
    """Detect file encoding"""
    try:
        # Try to read with UTF-8
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read()
        return 'utf-8'
    except UnicodeDecodeError:
        try:
            # Try UTF-8 with BOM
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                f.read()
            return 'utf-8-sig'
        except UnicodeDecodeError:
            # Fall back to latin-1
            return 'latin-1'

def detect_delimiter(filepath, encoding):
    """Detect CSV delimiter"""
    with open(filepath, 'r', encoding=encoding) as f:
        sample = f.read(1024)
        
    # Count occurrences of common delimiters
    comma_count = sample.count(',')
    semicolon_count = sample.count(';')
    tab_count = sample.count('\t')
    
    # Return the delimiter with the most occurrences
    if comma_count > semicolon_count and comma_count > tab_count:
        return ',', comma_count
    elif semicolon_count > tab_count:
        return ';', semicolon_count
    else:
        return '\t', tab_count

def parse_csv_file(filepath, verbose=False):
    """Parse and analyze a CSV file"""
    print(f"📄 Analyzing CSV file: {filepath}")
    
    # Check if file exists
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        return False
    
    # Detect encoding
    encoding = detect_encoding(filepath)
    print(f"🔤 Detected encoding: {encoding}")
    
    # Detect delimiter
    delimiter, count = detect_delimiter(filepath, encoding)
    print(f"🔍 Detected delimiter: '{delimiter}' ({count} occurrences in sample)")
    
    # Parse CSV
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            reader = csv.reader(f, delimiter=delimiter)
            
            # Read header
            try:
                headers = next(reader)
                print(f"📋 Headers ({len(headers)} columns):")
                for i, header in enumerate(headers):
                    print(f"   {i+1}. {header}")
            except StopIteration:
                print("❌ File is empty")
                return False
            
            # Validate expected headers
            expected_headers = ['phone', 'business_name', 'email']
            missing_headers = [h for h in expected_headers if h not in headers]
            unexpected_headers = [h for h in headers if h not in expected_headers]
            
            if missing_headers:
                print(f"❌ Missing expected headers: {missing_headers}")
            if unexpected_headers:
                print(f"⚠️  Unexpected headers: {unexpected_headers}")
            
            # Show sample rows
            print("\n📋 Sample rows:")
            row_count = 0
            for row in reader:
                row_count += 1
                if verbose or row_count <= 5:
                    print(f"   Row {row_count}: {row}")
                elif row_count == 6 and not verbose:
                    print(f"   ... ({row_count - 5} more rows)")
                    break
            
            print(f"\n📊 Total rows: {row_count}")
            
            # Check for common issues
            print("\n🔍 Issue Detection:")
            
            # Check for inconsistent column counts
            f.seek(0)
            next(reader)  # Skip header
            inconsistent_rows = []
            for i, row in enumerate(reader, start=2):  # Start at 2 because of header
                if len(row) != len(headers):
                    inconsistent_rows.append((i, len(row)))
            
            if inconsistent_rows:
                print(f"❌ Inconsistent column counts in {len(inconsistent_rows)} rows:")
                for row_num, col_count in inconsistent_rows[:5]:
                    print(f"   Row {row_num}: {col_count} columns (expected {len(headers)})")
                if len(inconsistent_rows) > 5:
                    print(f"   ... and {len(inconsistent_rows) - 5} more rows")
            else:
                print("✅ All rows have consistent column counts")
            
            return True
            
    except Exception as e:
        print(f"❌ Error parsing CSV file: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Parse and analyze CSV files for W3BHub')
    parser.add_argument('filepath', help='Path to CSV file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show all rows')
    
    args = parser.parse_args()
    
    print("📋 CSV Parser Tool for W3BHub")
    print("=" * 30)
    
    success = parse_csv_file(args.filepath, args.verbose)
    
    if success:
        print("\n✅ CSV file analysis completed")
        return 0
    else:
        print("\n❌ CSV file analysis failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())