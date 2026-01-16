#!/usr/bin/env python3
"""
Quick status check for the extraction process
"""

import os
from datetime import datetime
import re

LOG_FILE = '/Users/athessen/sleep-cde-schema/extraction_log.txt'
ERROR_FILE = '/Users/athessen/sleep-cde-schema/extraction_errors.txt'
CONT_OUTPUT = '/Users/athessen/sleep-cde-schema/continuous_variables_updated.tsv'
CAT_OUTPUT = '/Users/athessen/sleep-cde-schema/categorical_variables_updated.tsv'

def get_latest_progress():
    """Get the latest progress from log"""
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()

        # Find latest progress line
        for line in reversed(lines):
            if 'Progress:' in line:
                return line.strip()

        # Find latest processing line
        for line in reversed(lines):
            if 'Processing' in line:
                match = re.search(r'\[(\d+)/(\d+)\]', line)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    return f"Currently at: {current}/{total} ({current*100//total}%)"

        return "No progress found"
    except:
        return "Log file not found or empty"

def get_error_count():
    """Count errors"""
    try:
        with open(ERROR_FILE, 'r') as f:
            lines = f.readlines()
        # Skip header lines
        return max(0, len(lines) - 4)
    except:
        return 0

def get_file_size(path):
    """Get file size in MB"""
    try:
        size = os.path.getsize(path)
        return f"{size / 1024 / 1024:.2f} MB"
    except:
        return "Not created yet"

def get_row_count(path):
    """Get row count in TSV"""
    try:
        with open(path, 'r') as f:
            return len(f.readlines()) - 1  # Exclude header
    except:
        return 0

def estimate_completion(log_file):
    """Estimate completion time"""
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()

        # Find start time
        for line in lines:
            if 'Started:' in line:
                start_str = line.split('Started:')[1].strip()
                start_time = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S.%f')
                break

        # Find latest progress
        for line in reversed(lines):
            if 'Progress:' in line:
                match = re.search(r'(\d+)/(\d+)', line)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))

                    elapsed = datetime.now() - start_time
                    rate = current / elapsed.total_seconds()  # vars per second
                    remaining = (total - current) / rate  # seconds

                    return {
                        'current': current,
                        'total': total,
                        'elapsed': elapsed,
                        'rate': rate * 60,  # vars per minute
                        'remaining_seconds': remaining,
                        'eta': datetime.now().timestamp() + remaining
                    }

        return None
    except:
        return None

def main():
    print("=" * 70)
    print("NSRR VARIABLE METADATA EXTRACTION - STATUS")
    print("=" * 70)
    print()

    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Progress
    print("PROGRESS:")
    print(f"  {get_latest_progress()}")

    # Estimate
    est = estimate_completion(LOG_FILE)
    if est:
        print(f"  Rate: {est['rate']:.1f} variables/minute")
        print(f"  Elapsed: {est['elapsed']}")
        eta_time = datetime.fromtimestamp(est['eta'])
        print(f"  ETA: {eta_time.strftime('%H:%M:%S')} ({est['remaining_seconds']//60:.0f} min remaining)")

    print()

    # Errors
    error_count = get_error_count()
    print(f"ERRORS: {error_count}")
    if error_count > 0:
        print("  (Check extraction_errors.txt for details)")

    print()

    # Output files
    print("OUTPUT FILES:")
    cont_rows = get_row_count(CONT_OUTPUT)
    cat_rows = get_row_count(CAT_OUTPUT)

    print(f"  Continuous: {cont_rows} rows, {get_file_size(CONT_OUTPUT)}")
    print(f"  Categorical: {cat_rows} rows, {get_file_size(CAT_OUTPUT)}")

    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
