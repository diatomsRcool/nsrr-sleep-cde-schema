#!/usr/bin/env python3
"""
Update missing descriptions and visits in continuous_variables_cde.txt

This script:
1. Reads the existing file with curated data
2. Identifies rows with missing descriptions or visits
3. Fetches metadata from sleepdata.org for those variables
4. Updates ONLY missing information (does not overwrite existing data)
5. Outputs to a new TSV file
"""

import csv
import time
import requests
from bs4 import BeautifulSoup
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configuration
RATE_LIMIT_DELAY = 1.0  # seconds between requests
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

INPUT_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde.txt'
OUTPUT_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'

# Variables to skip (known to have no/bad data on sleepdata.org)
SKIP_VARIABLES = {
    'FDCSR/nsrr_age',  # Per user instruction: no data available
}

class VariablePageParser:
    """Parser for NSRR variable pages"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.cache = {}  # Cache for fetched pages

    def fetch_page(self, study: str, variable: str, retry_count=0) -> Optional[BeautifulSoup]:
        """Fetch and parse a variable page with retry logic"""
        cache_key = f"{study.lower()}/{variable}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        url = f"https://sleepdata.org/datasets/{study.lower()}/variables/{variable}"

        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)

            if response.status_code == 404:
                print(f"  [404] Variable page not found: {url}", file=sys.stderr)
                self.cache[cache_key] = None
                return None

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')
            self.cache[cache_key] = soup
            return soup

        except Exception as e:
            if retry_count < MAX_RETRIES:
                print(f"  Retry {retry_count + 1}/{MAX_RETRIES} for {study}/{variable}", file=sys.stderr)
                time.sleep(RETRY_DELAY)
                return self.fetch_page(study, variable, retry_count + 1)
            else:
                print(f"  [ERROR] Failed to fetch {url}: {e}", file=sys.stderr)
                self.cache[cache_key] = None
                return None

    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extract description from page"""
        if not soup:
            return ""

        # Strategy 1: Look for form-group with "Description" label specifically
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div:
                label_text = label_div.get_text(strip=True).lower()
                # Look specifically for description, not label
                if label_text == 'description':
                    value_div = form_group.find('div', class_='form-control-plaintext')
                    if value_div:
                        text = value_div.get_text(strip=True)
                        text = re.sub(r'\s+', ' ', text)
                        if text:
                            return text

        # Strategy 2: Look for description section
        desc_selectors = [
            {'class': 'variable-description'},
            {'class': 'description'},
            {'id': 'description'}
        ]

        for selector in desc_selectors:
            desc_elem = soup.find('div', selector)
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                text = re.sub(r'\s+', ' ', text)
                return text

        return ""

    def extract_visits_stats(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract visit statistics from the page.
        Returns list of dicts with visit info.
        """
        if not soup:
            return []

        stats_list = []

        # Look for statistics tables
        for table in soup.find_all('table'):
            header_row = table.find('tr')
            if not header_row:
                continue

            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

            # Check if this is a statistics table
            stats_headers = ['n', 'mean', 'median', 'min', 'max', 'std', 'stddev']
            if not any(h in headers for h in stats_headers):
                continue

            # Find column indices
            col_indices = {}
            for i, header in enumerate(headers):
                header_clean = header.lower().strip()
                if header_clean in ['n', 'count']:
                    col_indices['n'] = i
                elif header_clean in ['mean', 'average']:
                    col_indices['mean'] = i
                elif header_clean in ['std', 'stddev', 'std dev', 'stdev', 'sd']:
                    col_indices['stddev'] = i
                elif header_clean == 'median':
                    col_indices['median'] = i
                elif header_clean in ['min', 'minimum']:
                    col_indices['min'] = i
                elif header_clean in ['max', 'maximum']:
                    col_indices['max'] = i
                elif header_clean in ['unknown', 'missing', 'na']:
                    col_indices['unknown'] = i

            # Extract data rows
            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= 1:
                    continue

                visit_name = cells[0].get_text(strip=True)

                # Skip total/subtotal rows
                if visit_name.lower() in ['total', 'all', 'overall', '']:
                    continue

                # Skip demographic categories
                skip_keywords = ['male', 'female', 'treatment', 'arm', 'cpap', 'lgb',
                                'white', 'black', 'asian', 'hispanic', 'latino',
                                'race', 'ethnicity', 'gender', 'sex']

                visit_lower = visit_name.lower()
                if any(skip in visit_lower for skip in skip_keywords):
                    continue

                # Skip age ranges
                if re.search(r'\d+\.?\d*\s*(?:to|-)\s*\d+\.?\d*\s*(?:year|age)', visit_lower):
                    continue

                # Extract statistics
                visit_stats = {
                    'visit': visit_name,
                    'n': '',
                    'mean': '',
                    'stddev': '',
                    'median': '',
                    'min': '',
                    'max': '',
                    'unknown': '',
                }

                for stat_name, col_idx in col_indices.items():
                    if col_idx < len(cells):
                        value = cells[col_idx].get_text(strip=True)
                        value = value.replace('±', '').replace('\u00b1', '').strip()
                        # Keep the raw value for now
                        visit_stats[stat_name] = value

                stats_list.append(visit_stats)

        return stats_list


def read_input_file(filepath: str) -> Tuple[List[str], List[Dict]]:
    """Read the input TSV file and return headers and rows"""
    rows = []
    headers = []

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        headers = reader.fieldnames
        for row in reader:
            rows.append(row)

    return headers, rows


def identify_missing_data(rows: List[Dict]) -> Dict[str, set]:
    """
    Identify study/variable combinations with missing descriptions or visits.
    Returns dict mapping study_var key to set of what's missing.
    """
    missing = {}

    for row in rows:
        study = row.get('study_name', '')
        variable = row.get('variable_name', '')
        description = row.get('description', '')
        visit = row.get('visit', '')

        if not study or not variable:
            continue

        key = f"{study}/{variable}"

        needs_update = set()
        if not description.strip():
            needs_update.add('description')
        if not visit.strip():
            needs_update.add('visit')

        if needs_update:
            if key not in missing:
                missing[key] = set()
            missing[key].update(needs_update)

    return missing


def main():
    print(f"Reading input file: {INPUT_FILE}")
    headers, rows = read_input_file(INPUT_FILE)
    print(f"Found {len(rows)} rows with headers: {headers[:8]}...")

    # Identify what's missing
    missing = identify_missing_data(rows)

    # Remove skip variables
    for skip_key in SKIP_VARIABLES:
        if skip_key in missing:
            print(f"Skipping {skip_key} (in skip list)")
            del missing[skip_key]

    print(f"Found {len(missing)} unique study/variable combinations with missing data")

    # Count what's missing
    missing_desc = sum(1 for v in missing.values() if 'description' in v)
    missing_visit = sum(1 for v in missing.values() if 'visit' in v)
    print(f"  Missing descriptions: {missing_desc}")
    print(f"  Missing visits: {missing_visit}")

    # Create parser
    parser = VariablePageParser()

    # Group rows by study/variable for updating
    row_groups = {}
    for i, row in enumerate(rows):
        study = row.get('study_name', '')
        variable = row.get('variable_name', '')
        key = f"{study}/{variable}"
        if key not in row_groups:
            row_groups[key] = []
        row_groups[key].append((i, row))

    # Fetch and update missing data
    fetched = 0
    updated_desc = 0
    updated_visit = 0
    errors = 0
    skipped = 0

    # Process each unique study/variable with missing data
    for key in sorted(missing.keys()):
        parts = key.split('/')
        if len(parts) != 2:
            continue
        study, variable = parts

        # Skip known problematic variables
        if key in SKIP_VARIABLES:
            skipped += 1
            continue

        # Progress
        fetched += 1
        if fetched % 50 == 0 or fetched <= 10:
            print(f"[{fetched}/{len(missing)}] Processing {study}/{variable}...")

        # Fetch page
        soup = parser.fetch_page(study, variable)
        if not soup:
            errors += 1
            continue

        # Extract data
        extracted_desc = parser.extract_description(soup)
        extracted_visits = parser.extract_visits_stats(soup)

        # Update rows for this study/variable
        if key in row_groups:
            for idx, row in row_groups[key]:
                needs = missing.get(key, set())

                # Update description if missing
                if 'description' in needs and extracted_desc and not row.get('description', '').strip():
                    rows[idx]['description'] = extracted_desc
                    updated_desc += 1

                # Update visit if missing - match by looking at existing visit or statistics
                if 'visit' in needs and not row.get('visit', '').strip():
                    # Try to match visit by statistics if we have them
                    row_n = row.get('n', '').strip().replace(',', '').replace('"', '')
                    row_mean = row.get('mean', '').strip()

                    matched = False
                    for visit_data in extracted_visits:
                        # Simple match: if we have only one visit, use it
                        if len(extracted_visits) == 1:
                            rows[idx]['visit'] = visit_data['visit']
                            updated_visit += 1
                            matched = True
                            break

                        # Otherwise try to match by n or mean
                        visit_n = visit_data.get('n', '').replace(',', '').strip()
                        visit_mean = visit_data.get('mean', '').strip()

                        try:
                            if row_n and visit_n and row_n == visit_n:
                                rows[idx]['visit'] = visit_data['visit']
                                updated_visit += 1
                                matched = True
                                break
                            elif row_mean and visit_mean:
                                row_mean_f = float(row_mean)
                                visit_mean_f = float(visit_mean)
                                if abs(row_mean_f - visit_mean_f) < 0.1:
                                    rows[idx]['visit'] = visit_data['visit']
                                    updated_visit += 1
                                    matched = True
                                    break
                        except (ValueError, TypeError):
                            pass

                    if not matched and extracted_visits:
                        # If no match but we have visits, use the first one as fallback
                        # (only if there's exactly one row for this variable)
                        rows_for_var = row_groups.get(key, [])
                        if len(rows_for_var) == 1 and len(extracted_visits) >= 1:
                            rows[idx]['visit'] = extracted_visits[0]['visit']
                            updated_visit += 1

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

    print(f"\nProcessing complete:")
    print(f"  Fetched: {fetched}")
    print(f"  Updated descriptions: {updated_desc}")
    print(f"  Updated visits: {updated_visit}")
    print(f"  Errors: {errors}")
    print(f"  Skipped: {skipped}")

    # Write output
    print(f"\nWriting output to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)

    print("Done!")


if __name__ == "__main__":
    main()
