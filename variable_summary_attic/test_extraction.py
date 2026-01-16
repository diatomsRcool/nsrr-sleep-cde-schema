#!/usr/bin/env python3
"""
Test script for variable metadata extraction
Tests on a small sample of variables before running full extraction
"""

import sys
sys.path.insert(0, '/Users/athessen/sleep-cde-schema')

from extract_variable_metadata import VariablePageParser, Logger

# Test samples
TEST_CASES = [
    # Continuous with multi-visit
    ('abc', 'bmi', 'continuous'),
    # Continuous single visit
    ('abc', 'ess_total', 'continuous'),
    # Categorical
    ('abc', 'gender', 'categorical'),
    ('abc', 'race', 'categorical'),
    # Another study
    ('apoe', 'nsrr_age_gt89', 'categorical'),
]

def test_extraction():
    """Test extraction on sample variables"""
    logger = Logger(
        '/Users/athessen/sleep-cde-schema/test_extraction.log',
        '/Users/athessen/sleep-cde-schema/test_extraction_errors.log'
    )

    parser = VariablePageParser(logger)

    print("\n" + "=" * 80)
    print("TESTING VARIABLE EXTRACTION")
    print("=" * 80 + "\n")

    for study, variable, var_type in TEST_CASES:
        print(f"\nTesting {study}/{variable} ({var_type})")
        print("-" * 60)

        if var_type == 'continuous':
            results = parser.parse_continuous_variable(study, variable)
            print(f"Results: {len(results)} row(s)")
            for i, result in enumerate(results, 1):
                print(f"\nRow {i}:")
                for key, value in result.items():
                    if value:
                        print(f"  {key}: {value[:100] if len(str(value)) > 100 else value}")
        else:
            result = parser.parse_categorical_variable(study, variable)
            print("Results:")
            for key, value in result.items():
                if value:
                    print(f"  {key}: {value[:200] if len(str(value)) > 200 else value}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_extraction()
