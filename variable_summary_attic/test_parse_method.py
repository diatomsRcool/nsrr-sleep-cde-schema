#!/usr/bin/env python3
"""Test the actual parse_continuous_variable method"""

import sys
sys.path.insert(0, '/Users/athessen/sleep-cde-schema')

from extract_variable_metadata import VariablePageParser, Logger

# Create logger
logger = Logger('/tmp/test_parse.log', '/tmp/test_parse_errors.log')

# Create parser
parser = VariablePageParser(logger)

# Test parse_continuous_variable
print("Testing parse_continuous_variable for ABC/BMI...")
result = parser.parse_continuous_variable('abc', 'bmi')

print(f"\nReturned {len(result)} rows:")
for i, row in enumerate(result, 1):
    print(f"\nRow {i}:")
    for key, value in row.items():
        if value:
            print(f"  {key}: '{value}'")
        else:
            print(f"  {key}: (empty/falsy)")
