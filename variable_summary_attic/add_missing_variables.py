#!/usr/bin/env python3
"""
Add missing variables from catvcon.txt to the appropriate files.
Fetches full metadata from sleepdata.org including visits and statistics.
"""

import csv
import time
import requests
from bs4 import BeautifulSoup
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

# Configuration
RATE_LIMIT_DELAY = 1.0
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

CATVCON_FILE = '/Users/athessen/sleep-cde-schema/catvcon.txt'
CONTINUOUS_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'
CATEGORICAL_FILE = '/Users/athessen/sleep-cde-schema/categorical_variables_cde_updated.tsv'


class VariablePageParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.cache = {}

    def fetch_page(self, study: str, variable: str, retry_count=0) -> Optional[BeautifulSoup]:
        cache_key = f"{study.lower()}/{variable}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        url = f"https://sleepdata.org/datasets/{study.lower()}/variables/{variable}"

        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 404:
                self.cache[cache_key] = None
                return None
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')
            self.cache[cache_key] = soup
            return soup

        except Exception as e:
            if retry_count < MAX_RETRIES:
                time.sleep(5)
                return self.fetch_page(study, variable, retry_count + 1)
            else:
                print(f"  [ERROR] Failed to fetch {url}: {e}", file=sys.stderr)
                self.cache[cache_key] = None
                return None

    def extract_metadata(self, soup: BeautifulSoup) -> Dict:
        """Extract variable metadata from the page."""
        if not soup:
            return {}

        metadata = {}

        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            value_div = form_group.find('div', class_='form-control-plaintext')
            if label_div and value_div:
                label = label_div.get_text(strip=True).lower()
                value = value_div.get_text(strip=True)
                value = re.sub(r'\s+', ' ', value)

                if label == 'label':
                    metadata['variable_label'] = value
                elif label == 'description':
                    metadata['description'] = value
                elif label == 'calculation':
                    metadata['calculation'] = value
                elif label == 'type':
                    metadata['type'] = value
                elif label == 'units':
                    metadata['units'] = value
                elif label == 'folder':
                    metadata['folder'] = value

        # Try to get folder from breadcrumb if not in form
        if 'folder' not in metadata:
            breadcrumb = soup.find('ol', class_='breadcrumb')
            if breadcrumb:
                items = breadcrumb.find_all('li')
                folder_parts = []
                for item in items[2:-1]:
                    text = item.get_text(strip=True)
                    if text and text not in ['Variables', 'Home']:
                        folder_parts.append(text)
                if folder_parts:
                    metadata['folder'] = '/'.join(folder_parts)

        return metadata

    def extract_domain(self, soup: BeautifulSoup) -> str:
        """Extract domain/choices for categorical variables."""
        if not soup:
            return ""

        # Look for bullet list with code:value format
        for ul in soup.find_all(['ul', 'ol']):
            choices = []
            for li in ul.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                match = re.match(r'^([0-9a-zA-Z_]+)\s*[:\-]\s*(.+)$', text)
                if match:
                    code = match.group(1).strip()
                    label = match.group(2).strip()
                    label = re.sub(r'\s+', ' ', label)
                    choices.append(f"{code}:{label}")

            if len(choices) >= 2:
                return '|'.join(choices)

        return ""

    def extract_all_visits(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all visit data from the statistics tables."""
        if not soup:
            return []

        visits = []

        for table in soup.find_all('table'):
            header_row = table.find('tr')
            if not header_row:
                continue

            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

            # Check if this is a statistics table
            stats_headers = ['n', 'mean', 'median', 'min', 'max', 'std', 'stddev', 'total']
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
                elif header_clean == 'total':
                    col_indices['total_subjects'] = i

            # Extract data rows
            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= 1:
                    continue

                visit_name = cells[0].get_text(strip=True)

                # Skip total/subtotal rows and demographic categories
                if visit_name.lower() in ['total', 'all', 'overall', '']:
                    continue

                skip_keywords = ['male', 'female', 'treatment', 'arm', 'white', 'black',
                               'asian', 'hispanic', 'latino', 'race', 'ethnicity', 'gender', 'sex']
                visit_lower = visit_name.lower()
                if any(skip in visit_lower for skip in skip_keywords):
                    continue

                # Skip age ranges
                if re.search(r'\d+\.?\d*\s*(?:to|-)\s*\d+\.?\d*\s*(?:year|age)', visit_lower):
                    continue

                # Extract statistics
                visit_data = {'visit': visit_name}
                for stat_name, col_idx in col_indices.items():
                    if col_idx < len(cells):
                        value = cells[col_idx].get_text(strip=True)
                        value = value.replace('±', '').replace('\u00b1', '').strip()
                        visit_data[stat_name] = value if value and value not in ['-', '—'] else ''

                visits.append(visit_data)

            # Only use the first statistics table
            if visits:
                break

        return visits


def main():
    print("=== Adding Missing Variables ===\n")

    # Read catvcon.txt
    catvcon = []
    with open(CATVCON_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            catvcon.append(row)

    print(f"Total variables in catvcon.txt: {len(catvcon)}")

    # Read existing continuous variables
    continuous_existing = set()
    continuous_rows = []
    with open(CONTINUOUS_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        continuous_headers = reader.fieldnames
        for row in reader:
            key = (row.get('study_name', ''), row.get('variable_name', ''))
            continuous_existing.add(key)
            continuous_rows.append(row)

    print(f"Existing continuous variables: {len(continuous_existing)}")

    # Read existing categorical variables
    categorical_existing = set()
    categorical_rows = []
    with open(CATEGORICAL_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        categorical_headers = reader.fieldnames
        for row in reader:
            key = (row.get('study_name', ''), row.get('variable_name', ''))
            categorical_existing.add(key)
            categorical_rows.append(row)

    print(f"Existing categorical variables: {len(categorical_existing)}")

    # Find missing variables
    missing_continuous = []
    missing_categorical = []

    for row in catvcon:
        study = row.get('study_name', '').strip()
        var = row.get('variable_name', '').strip()
        cat = row.get('category', '').strip().lower()

        key = (study, var)

        if cat == 'continuous':
            if key not in continuous_existing:
                missing_continuous.append((study, var))
        elif cat == 'categorical':
            if key not in categorical_existing:
                missing_categorical.append((study, var))

    print(f"\nMissing continuous: {len(missing_continuous)}")
    print(f"Missing categorical: {len(missing_categorical)}")

    # Fetch and add missing continuous variables
    parser = VariablePageParser()
    new_continuous_rows = []

    print(f"\n=== Fetching {len(missing_continuous)} missing continuous variables ===")

    for i, (study, variable) in enumerate(missing_continuous):
        if (i + 1) % 20 == 0 or i < 5:
            print(f"[{i+1}/{len(missing_continuous)}] Fetching {study}/{variable}...")

        soup = parser.fetch_page(study, variable)
        if not soup:
            continue

        metadata = parser.extract_metadata(soup)
        visits = parser.extract_all_visits(soup)

        if not visits:
            # Create a single row without visit data
            new_row = {
                'study_name': study,
                'variable_name': variable,
                'variable_label': metadata.get('variable_label', ''),
                'folder': metadata.get('folder', ''),
                'description': metadata.get('description', ''),
                'visit': '',
                'calculation': metadata.get('calculation', ''),
                'type': metadata.get('type', 'numeric'),
                'total_subjects': '',
                'units': metadata.get('units', ''),
                'n': '',
                'mean': '',
                'stddev': '',
                'median': '',
                'min': '',
                'max': '',
                'unknown': '',
            }
            new_continuous_rows.append(new_row)
        else:
            # Create a row for each visit
            for visit_data in visits:
                new_row = {
                    'study_name': study,
                    'variable_name': variable,
                    'variable_label': metadata.get('variable_label', ''),
                    'folder': metadata.get('folder', ''),
                    'description': metadata.get('description', ''),
                    'visit': visit_data.get('visit', ''),
                    'calculation': metadata.get('calculation', ''),
                    'type': metadata.get('type', 'numeric'),
                    'total_subjects': visit_data.get('total_subjects', ''),
                    'units': metadata.get('units', ''),
                    'n': visit_data.get('n', ''),
                    'mean': visit_data.get('mean', ''),
                    'stddev': visit_data.get('stddev', ''),
                    'median': visit_data.get('median', ''),
                    'min': visit_data.get('min', ''),
                    'max': visit_data.get('max', ''),
                    'unknown': visit_data.get('unknown', ''),
                }
                new_continuous_rows.append(new_row)

        time.sleep(RATE_LIMIT_DELAY)

    print(f"\nAdded {len(new_continuous_rows)} new continuous rows")

    # Fetch and add missing categorical variables
    new_categorical_rows = []

    if missing_categorical:
        print(f"\n=== Fetching {len(missing_categorical)} missing categorical variables ===")

        for i, (study, variable) in enumerate(missing_categorical):
            if (i + 1) % 20 == 0 or i < 5:
                print(f"[{i+1}/{len(missing_categorical)}] Fetching {study}/{variable}...")

            soup = parser.fetch_page(study, variable)
            if not soup:
                continue

            metadata = parser.extract_metadata(soup)
            domain = parser.extract_domain(soup)

            new_row = {
                'study_name': study,
                'variable_name': variable,
                'variable_label': metadata.get('variable_label', ''),
                'folder': metadata.get('folder', ''),
                'description': metadata.get('description', ''),
                'domain': domain,
                'type': metadata.get('type', 'choices'),
            }
            new_categorical_rows.append(new_row)

            time.sleep(RATE_LIMIT_DELAY)

        print(f"\nAdded {len(new_categorical_rows)} new categorical rows")

    # Write updated continuous file
    all_continuous = continuous_rows + new_continuous_rows
    all_continuous.sort(key=lambda r: (r.get('study_name', ''), r.get('variable_name', ''), r.get('visit', '')))

    print(f"\nWriting {len(all_continuous)} rows to continuous file...")
    with open(CONTINUOUS_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=continuous_headers, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_continuous)

    # Write updated categorical file
    if new_categorical_rows:
        all_categorical = categorical_rows + new_categorical_rows
        all_categorical.sort(key=lambda r: (r.get('study_name', ''), r.get('variable_name', '')))

        print(f"Writing {len(all_categorical)} rows to categorical file...")
        with open(CATEGORICAL_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=categorical_headers, delimiter='\t', extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_categorical)

    print("\nDone!")

    # Summary
    print("\n=== Summary ===")
    print(f"New continuous rows added: {len(new_continuous_rows)}")
    print(f"New categorical rows added: {len(new_categorical_rows)}")
    print(f"Total continuous rows: {len(all_continuous)}")
    print(f"Total categorical rows: {len(categorical_rows) + len(new_categorical_rows)}")


if __name__ == "__main__":
    main()
