#!/usr/bin/env python3
"""
Update curated variable files with information from sleepdata.org
"""

import csv
import time
import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Configuration
RATE_LIMIT_DELAY = 1.5  # seconds between requests
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# File paths
CONTINUOUS_INPUT = '/Users/athessen/sleep-cde-schema/continuous_variables_updated_curated.txt'
CATEGORICAL_INPUT = '/Users/athessen/sleep-cde-schema/categorical_variables_updated_curated.txt'
CONTINUOUS_OUTPUT = '/Users/athessen/sleep-cde-schema/continuous_variables_updated_curated_final.tsv'
CATEGORICAL_OUTPUT = '/Users/athessen/sleep-cde-schema/categorical_variables_updated_curated_final.tsv'

class VariablePageParser:
    """Parser for NSRR variable pages"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        # Cache for storing extracted data by (study, variable)
        self.cache = {}

    def fetch_page(self, study: str, variable: str, retry_count=0) -> Optional[BeautifulSoup]:
        """Fetch and parse a variable page with retry logic"""
        # IMPORTANT: URLs are case-sensitive, study names must be lowercase
        url = f"https://sleepdata.org/datasets/{study.lower()}/variables/{variable}"

        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)

            if response.status_code == 404:
                print(f"  ⚠️  Variable page not found: {url}")
                return None

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            return BeautifulSoup(response.text, 'html.parser')

        except Exception as e:
            if retry_count < MAX_RETRIES:
                print(f"  Retry {retry_count + 1}/{MAX_RETRIES} for {study}/{variable}")
                time.sleep(RETRY_DELAY)
                return self.fetch_page(study, variable, retry_count + 1)
            else:
                print(f"  ❌ Failed to fetch {url}: {e}")
                return None

    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extract full description from page"""
        # Look for form-group with Label
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div and 'label' in label_div.get_text().lower():
                value_div = form_group.find('div', class_='form-control-plaintext')
                if value_div:
                    text = value_div.get_text(strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    return text
        return ""

    def extract_calculation(self, soup: BeautifulSoup) -> str:
        """Extract calculation/formula from page"""
        # Look for form-group with Calculation or Formula
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div:
                label_text = label_div.get_text().lower()
                if 'calculation' in label_text or 'formula' in label_text:
                    value_div = form_group.find('div', class_='form-control-plaintext')
                    if value_div:
                        text = value_div.get_text(strip=True)
                        text = re.sub(r'\s+', ' ', text)
                        return text
        return ""

    def extract_type(self, soup: BeautifulSoup) -> str:
        """Extract variable type"""
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div and 'type' in label_div.get_text().lower():
                value_div = form_group.find('div', class_='form-control-plaintext')
                if value_div:
                    return value_div.get_text(strip=True)
        return ""

    def extract_units(self, soup: BeautifulSoup) -> str:
        """Extract units for continuous variables"""
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div and 'units' in label_div.get_text().lower():
                value_div = form_group.find('div', class_='form-control-plaintext')
                if value_div:
                    units = value_div.get_text(strip=True)
                    units = re.sub(r'\s+', ' ', units)
                    return units
        return ""

    def extract_domain(self, soup: BeautifulSoup) -> str:
        """Extract domain/choices for categorical variables in pipe-delimited format"""
        # Strategy 1: Look for bullet list with code:value format
        for ul in soup.find_all(['ul', 'ol']):
            choices = []
            for li in ul.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                # Try to parse "code: label" or "code - label" format
                match = re.match(r'^([0-9a-zA-Z]+)\s*[:\-]\s*(.+)$', text)
                if match:
                    code = match.group(1).strip()
                    label = match.group(2).strip()
                    label = re.sub(r'\s+', ' ', label)
                    choices.append(f"{code}:{label}")

            if len(choices) >= 2:
                return '|'.join(choices)

        # Strategy 2: Look for tables with code/value columns
        for table in soup.find_all('table'):
            header_row = table.find('tr')
            if not header_row:
                continue

            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

            code_col = None
            label_col = None

            for i, header in enumerate(headers):
                if header in ['code', 'value', 'id', 'number', 'key']:
                    code_col = i
                elif header in ['label', 'description', 'meaning', 'text', 'name', 'category']:
                    label_col = i

            if code_col is not None and label_col is not None:
                choices = []
                for row in table.find_all('tr')[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > max(code_col, label_col):
                        code = cells[code_col].get_text(strip=True)
                        label = cells[label_col].get_text(strip=True)

                        if not code or not label or code.lower() in headers:
                            continue

                        label = re.sub(r'\s+', ' ', label)
                        choices.append(f"{code}:{label}")

                if choices:
                    return '|'.join(choices)

        return ""

    def extract_statistics(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract statistics for continuous variables"""
        stats_list = []

        # Look for statistics table
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

                # Skip totals and demographics
                if visit_name.lower() in ['total', 'all', 'overall', '']:
                    continue

                visit_keywords = ['baseline', 'followup', 'follow-up', 'month', 'year', 'visit',
                                  'screening', 'week', 'day', 'v1', 'v2', 'v3', 'v4', 'v5',
                                  'pre', 'post', 'initial', 'final', 'cycle', 'phase']

                skip_keywords = ['male', 'female', 'treatment', 'arm', 'cpap', 'lgb',
                                'white', 'black', 'asian', 'hispanic', 'latino',
                                'race', 'ethnicity', 'gender', 'sex']

                visit_lower = visit_name.lower()

                if any(skip in visit_lower for skip in skip_keywords):
                    continue

                if re.search(r'\d+\.?\d*\s*(?:to|-)\s*\d+\.?\d*\s*(?:year|age)', visit_lower):
                    continue

                if not any(keyword in visit_lower for keyword in visit_keywords):
                    continue

                # Extract statistics from this row
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
                        value = value.replace('±', '').strip()
                        value = re.sub(r'[^\d.\-]', '', value)
                        visit_stats[stat_name] = value

                stats_list.append(visit_stats)

        return stats_list

    def get_variable_info(self, study: str, variable: str) -> Dict:
        """Get all info for a variable, using cache if available"""
        cache_key = (study.upper(), variable)

        if cache_key in self.cache:
            return self.cache[cache_key]

        print(f"  Fetching {study}/{variable}...")
        soup = self.fetch_page(study, variable)

        if not soup:
            return {}

        info = {
            'description': self.extract_description(soup),
            'calculation': self.extract_calculation(soup),
            'type': self.extract_type(soup),
            'units': self.extract_units(soup),
            'domain': self.extract_domain(soup),
            'statistics': self.extract_statistics(soup)
        }

        self.cache[cache_key] = info
        time.sleep(RATE_LIMIT_DELAY)

        return info


def update_continuous_variables():
    """Update continuous variables file"""
    print("\n" + "="*80, flush=True)
    print("UPDATING CONTINUOUS VARIABLES", flush=True)
    print("="*80 + "\n", flush=True)

    parser = VariablePageParser()

    # Read input (files use ISO-8859-1 encoding)
    with open(CONTINUOUS_INPUT, 'r', encoding='iso-8859-1') as f:
        reader = csv.DictReader(f, delimiter='\t')
        input_rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"Found {len(input_rows)} rows to process\n", flush=True)

    # Group rows by (study, variable) to avoid redundant lookups
    variable_groups = defaultdict(list)
    for i, row in enumerate(input_rows):
        key = (row['study_name'], row['variable_name'])
        variable_groups[key].append(i)

    print(f"Found {len(variable_groups)} unique variables\n", flush=True)

    # Process each unique variable
    for idx, ((study, variable), row_indices) in enumerate(variable_groups.items(), 1):
        print(f"[{idx}/{len(variable_groups)}] Processing {study}/{variable} ({len(row_indices)} rows)", flush=True)

        # Get info from page
        info = parser.get_variable_info(study, variable)

        # Update all rows for this variable
        for row_idx in row_indices:
            row = input_rows[row_idx]

            # Update description if available
            if info.get('description'):
                row['description'] = info['description']

            # Update calculation if available
            if info.get('calculation'):
                row['calculation'] = info['calculation']

            # For rows without statistics, try to fill them in
            if not row.get('n') and info.get('statistics'):
                # Try to match by visit or use first available
                stats = info['statistics']

                if stats:
                    # If row has visit, try to match it
                    if row.get('visit'):
                        matching_stat = None
                        for stat in stats:
                            if stat['visit'] == row['visit']:
                                matching_stat = stat
                                break

                        if matching_stat:
                            for key in ['n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown']:
                                if matching_stat.get(key):
                                    row[key] = matching_stat[key]
                    else:
                        # No visit in row, use first available stat
                        if len(stats) > 0:
                            stat = stats[0]
                            if stat.get('visit'):
                                row['visit'] = stat['visit']
                            for key in ['n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown']:
                                if stat.get(key):
                                    row[key] = stat[key]

            # Fill in units if missing
            if not row.get('units') and info.get('units'):
                row['units'] = info['units']

            # Fill in type if missing
            if not row.get('type') and info.get('type'):
                row['type'] = info['type']

    # Write output
    print(f"\nWriting results to: {CONTINUOUS_OUTPUT}")
    with open(CONTINUOUS_OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(input_rows)

    print(f"✅ Continuous variables complete: {len(input_rows)} rows written")


def update_categorical_variables():
    """Update categorical variables file"""
    print("\n" + "="*80)
    print("UPDATING CATEGORICAL VARIABLES")
    print("="*80 + "\n")

    parser = VariablePageParser()

    # Read input (files use ISO-8859-1 encoding)
    with open(CATEGORICAL_INPUT, 'r', encoding='iso-8859-1') as f:
        reader = csv.DictReader(f, delimiter='\t')
        input_rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"Found {len(input_rows)} rows to process\n")

    # Process each variable
    for idx, row in enumerate(input_rows, 1):
        study = row['study_name']
        variable = row['variable_name']

        print(f"[{idx}/{len(input_rows)}] Processing {study}/{variable}")

        # Get info from page
        info = parser.get_variable_info(study, variable)

        # Update description if available
        if info.get('description'):
            row['description'] = info['description']

        # Update domain if available
        if info.get('domain'):
            row['domain'] = info['domain']

    # Write output
    print(f"\nWriting results to: {CATEGORICAL_OUTPUT}")
    with open(CATEGORICAL_OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(input_rows)

    print(f"✅ Categorical variables complete: {len(input_rows)} rows written")


def main():
    """Main execution function"""
    start_time = time.time()

    print("\n" + "="*80, flush=True)
    print("NSRR VARIABLE CURATED FILES UPDATE", flush=True)
    print("="*80, flush=True)

    # Update continuous variables
    update_continuous_variables()

    # Update categorical variables
    update_categorical_variables()

    duration = time.time() - start_time
    print("\n" + "="*80)
    print(f"✅ UPDATE COMPLETE")
    print("="*80)
    print(f"Duration: {duration/60:.1f} minutes")
    print(f"Output files:")
    print(f"  - {CONTINUOUS_OUTPUT}")
    print(f"  - {CATEGORICAL_OUTPUT}")
    print()


if __name__ == "__main__":
    main()
