#!/usr/bin/env python3
"""Test if debug logging works"""

import sys
sys.path.insert(0, '/Users/athessen/sleep-cde-schema')

from extract_variable_metadata import VariablePageParser, Logger

# Create logger
logger = Logger('/tmp/test_debug.log', '/tmp/test_debug_errors.log')

# Create parser
parser = VariablePageParser(logger)

# Fetch BMI page
soup = parser.fetch_page('abc', 'bmi')

if soup:
    print("Fetched BMI page successfully")
    print(f"Found {len(soup.find_all('table'))} tables")

    # Call extract_statistics with debug=True
    print("\nCalling extract_statistics with debug=True...")
    stats = parser.extract_statistics(soup, debug=True)

    print(f"\nReturned {len(stats)} statistics rows")
    for i, stat in enumerate(stats, 1):
        print(f"Row {i}: visit='{stat.get('visit')}', n='{stat.get('n')}', mean='{stat.get('mean')}'")

    # Check log file
    print("\n" + "="*80)
    print("LOG FILE CONTENTS:")
    print("="*80)
    with open('/tmp/test_debug.log', 'r') as f:
        print(f.read())
