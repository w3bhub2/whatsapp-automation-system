#!/usr/bin/env python3
"""
CSV Validation Script for W3BHub WhatsApp Automation System

This script implements the data validation harness requirement:
- Add strict CSV schema validator
- Validator produces deterministic error messages
"""

import csv
import re
import sys
import json
from pathlib import Path

# Expected CSV schema
EXPECTED_SCHEMA = {
    'phone': {
        'required': True,
        'type': 'string',
        'validation': r'^[0-9]{10,15}$',  # 10-15 digits
        'description': 'Phone number (10-15 digits)'
    },
    'business_name': {
        'required': True,
        'type': 'string',
        'min_length': 1,
        'max_length': 100,
        'description': 'Business name'
    },
    'email': {
        'required': False,
        'type': 'string',
        'validation': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'description': 'Email address (optional)'
    }
}

def validate_phone(value):
    """Validate phone number"""
    if not value:
        return False, "Phone number is required"
    
    if not re.match(r'^[0-9]{10,15}$', value):
        return False, "Phone number must be 10-15 digits"
    
    return True, ""

def validate_business_name(value):
    """Validate business name"""
    if not value:
        return False, "Business name is required"
    
    if len(value) < 1:
        return False, "Business name cannot be empty"
    
    if len(value) > 100:
        return False, "Business name too long (max 100 characters)"
    
    return True, ""

def validate_email(value):
    """Validate email address"""
    if not value:
        return True, ""  # Email is optional
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
        return False, "Invalid email format"
    
    return True, ""

VALIDATORS = {
    'phone': validate_phone,
    'business_name': validate_business_name,
    'email': validate_email
}

def validate_csv_row(row, row_number, headers):
    """Validate a single CSV row"""
    errors = []
    
    # Check if row has the right number of columns
    if len(row) != len(headers):
        errors.append(f"Row {row_number}: Expected {len(headers)} columns, got {len(row)}")
        return errors
    
    # Validate each field
    for i, field_name in enumerate(headers):
        if field_name in EXPECTED_SCHEMA:
            field_value = row[i] if i < len(row) else ""
            is_required = EXPECTED_SCHEMA[field_name]['required']
            
            # Check if required field is missing
            if is_required and not field_value:
                errors.append(f"Row {row_number}: {field_name} is required")
                continue
            
            # Run field-specific validation
            if field_name in VALIDATORS:
                is_valid, error_msg = VALIDATORS[field_name](field_value)
                if not is_valid:
                    errors.append(f"Row {row_number}: {field_name} - {error_msg}")
        else:
            # Unexpected field
            errors.append(f"Row {row_number}: Unexpected field '{field_name}'")
    
    return errors

def validate_csv_file(filepath):
    """Validate a CSV file against the expected schema"""
    print(f"📄 Validating CSV file: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            # Check for BOM
            csvfile.seek(0)
            first_bytes = csvfile.read(4)
            if first_bytes.startswith('\ufeff'):
                print("⚠️  File contains UTF-8 BOM")
            csvfile.seek(0)
            
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            if '\t' in sample and ',' not in sample:
                delimiter = '\t'
                print("🔍 Detected tab delimiter")
            elif ';' in sample and ',' not in sample:
                delimiter = ';'
                print("🔍 Detected semicolon delimiter")
            else:
                delimiter = ','
                print("🔍 Detected comma delimiter")
            
            # Parse CSV
            reader = csv.reader(csvfile, delimiter=delimiter)
            
            # Read header
            try:
                headers = next(reader)
            except StopIteration:
                return [{
                    'error': 'Empty file',
                    'details': 'File contains no data'
                }]
            
            print(f"📋 Headers: {', '.join(headers)}")
            
            # Validate headers
            header_errors = []
            for expected_field in EXPECTED_SCHEMA:
                if EXPECTED_SCHEMA[expected_field]['required'] and expected_field not in headers:
                    header_errors.append(f"Missing required field: {expected_field}")
            
            for actual_field in headers:
                if actual_field not in EXPECTED_SCHEMA:
                    header_errors.append(f"Unexpected field: {actual_field}")
            
            if header_errors:
                return [{'error': 'Header validation failed', 'details': header_errors}]
            
            # Validate rows
            row_errors = []
            row_number = 1  # Start at 1 because we already read the header
            
            for row in reader:
                row_number += 1
                errors = validate_csv_row(row, row_number, headers)
                if errors:
                    row_errors.extend(errors)
                
                # Limit output for large files
                if row_number > 1000 and len(row_errors) > 50:
                    row_errors.append(f"Stopped validation after {row_number} rows due to too many errors")
                    break
            
            return row_errors
            
    except UnicodeDecodeError as e:
        return [{
            'error': 'Encoding error',
            'details': f'File encoding issue: {str(e)}. Try converting to UTF-8.'
        }]
    except Exception as e:
        return [{
            'error': 'File processing error',
            'details': str(e)
        }]

def create_sample_csv():
    """Create a sample CSV file for testing"""
    sample_content = """phone,business_name,email
919876543210,ABC Shop,contact@abcshop.com
919876543211,XYZ Store,info@xyzstore.com
919876543212,123 Services,services@123.com
919876543213,Tech Solutions,tech@solutions.com
919876543214,Fashion Hub,fashion@hub.com"""
    
    with open('sample_leads.csv', 'w', newline='', encoding='utf-8') as f:
        f.write(sample_content)
    
    print("✅ Sample CSV file created: sample_leads.csv")

def main():
    """Main function"""
    print("📋 CSV Schema Validator for W3BHub")
    print("=" * 40)
    
    # Create diagnostics directory if it doesn't exist
    Path("diagnostics/csv-fails").mkdir(parents=True, exist_ok=True)
    
    # If no arguments provided, validate all CSV files in current directory
    if len(sys.argv) < 2:
        # Look for CSV files
        csv_files = [f for f in Path('.').iterdir() if f.suffix.lower() == '.csv']
        
        if not csv_files:
            print("❌ No CSV files found in current directory")
            print("Creating sample CSV file for testing...")
            create_sample_csv()
            csv_files = [Path('sample_leads.csv')]
        
        print(f"📁 Found {len(csv_files)} CSV file(s)")
        
        all_results = {}
        for csv_file in csv_files:
            print(f"\n🔍 Processing {csv_file.name}...")
            errors = validate_csv_file(str(csv_file))
            all_results[csv_file.name] = errors
            
            if errors:
                print(f"❌ Validation failed for {csv_file.name}:")
                for error in errors[:10]:  # Show first 10 errors
                    if isinstance(error, dict):
                        print(f"  - {error['error']}: {error['details']}")
                    else:
                        print(f"  - {error}")
                if len(errors) > 10:
                    print(f"  ... and {len(errors) - 10} more errors")
            else:
                print(f"✅ {csv_file.name} is valid")
        
        # Save results
        with open('diagnostics/csv-validation-report.json', 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n💾 Validation report saved to diagnostics/csv-validation-report.json")
        
    else:
        # Validate specific file
        filepath = sys.argv[1]
        errors = validate_csv_file(filepath)
        
        if errors:
            print(f"❌ Validation failed for {filepath}:")
            for error in errors:
                if isinstance(error, dict):
                    print(f"  - {error['error']}: {error['details']}")
                else:
                    print(f"  - {error}")
            return 1
        else:
            print(f"✅ {filepath} is valid")
            return 0

if __name__ == "__main__":
    sys.exit(main())