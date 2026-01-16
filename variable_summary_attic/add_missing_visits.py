#!/usr/bin/env python3
"""
Add missing visit rows for variables in specified studies.
For each variable, fetch the sleepdata.org page and add rows for visits
that are not yet in the file.
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

INPUT_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'
OUTPUT_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'

# Target visits by study
TARGET_VISITS = {
    'ANSWERS': ['Cross-Sectional Survey'],
    'APPLES': ['Baseline (BL)', 'Clinical Evaluation (CE)', 'Diagnostic Visit (DX)',
               'CPAP Titration Visit (CPAP)', 'Two Month Post-CPAP Neurocognitive Visit (2M)',
               'Four Month Post-CPAP Neurocognitive Visit (4M)', 'Six Month Post-CPAP Neurocognitive Visit (6M)'],
    'HCHS': ['Sueno Ancillary'],
    'LOFTHF': ['Follow-up On Treatment'],
    'NCHSDB': ['Second overnight sleep study', 'Third overnight sleep study',
               'Fourth overnight sleep study', 'Fifth overnight sleep study'],
    'SANDD': ['12 mo[1yr] follow up', '18mo[1.5yr]', '24mo[2yr]', '30mo[2.5y]'],
    'SHHS': ['CVD Outcomes'],
    'SHINE': ['Intake'],
    'WSC': ['Mailed Survey'],
}


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
                # Skip first items (Home, Dataset name) and last (variable name)
                folder_parts = []
                for item in items[2:-1]:
                    text = item.get_text(strip=True)
                    if text and text not in ['Variables', 'Home']:
                        folder_parts.append(text)
                if folder_parts:
                    metadata['folder'] = '/'.join(folder_parts)

        return metadata

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

            # Only use the first statistics table (others are usually demographic breakdowns)
            if visits:
                break

        return visits


def normalize_visit(visit: str) -> str:
    """Normalize visit name for comparison."""
    return visit.lower().strip().replace('ñ', 'n').replace('�', 'n')


def visit_matches(target: str, actual: str) -> bool:
    """Check if two visit names match (allowing for encoding differences)."""
    target_norm = normalize_visit(target)
    actual_norm = normalize_visit(actual)

    # Exact match
    if target_norm == actual_norm:
        return True

    # Partial match (one contains the other)
    if target_norm in actual_norm or actual_norm in target_norm:
        return True

    # Handle Sueno/Sueño
    if 'sueno' in target_norm and 'sueno' in actual_norm:
        return True

    return False


def main():
    print(f"Reading input file: {INPUT_FILE}")

    # Read all rows
    rows = []
    with open(INPUT_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        headers = reader.fieldnames
        for row in reader:
            rows.append(row)

    print(f"Found {len(rows)} rows")

    # Build index of existing study/variable/visit combinations
    existing = {}  # key: (study, variable) -> set of visits
    var_templates = {}  # key: (study, variable) -> template row with metadata

    for row in rows:
        study = row.get('study_name', '')
        variable = row.get('variable_name', '')
        visit = row.get('visit', '')

        key = (study, variable)
        if key not in existing:
            existing[key] = set()
            var_templates[key] = row.copy()  # Use first row as template

        existing[key].add(normalize_visit(visit))

    # Get unique variables to process
    vars_to_process = []
    for study in TARGET_VISITS.keys():
        study_vars = set(r['variable_name'] for r in rows if r.get('study_name') == study)
        for var in study_vars:
            vars_to_process.append((study, var))

    print(f"Processing {len(vars_to_process)} unique study/variable combinations")

    # Fetch and add missing visits
    parser = VariablePageParser()
    new_rows = []
    processed = 0

    for study, variable in sorted(vars_to_process):
        processed += 1
        if processed % 20 == 0 or processed <= 5:
            print(f"[{processed}/{len(vars_to_process)}] Processing {study}/{variable}...")

        # Fetch page
        soup = parser.fetch_page(study, variable)
        if not soup:
            continue

        # Extract metadata and visits
        metadata = parser.extract_metadata(soup)
        web_visits = parser.extract_all_visits(soup)

        if not web_visits:
            continue

        # Get template row
        key = (study, variable)
        template = var_templates.get(key, {})
        existing_visits = existing.get(key, set())

        # Target visits for this study
        target_visits = TARGET_VISITS.get(study, [])

        # Check each web visit against targets
        for web_visit in web_visits:
            web_visit_name = web_visit.get('visit', '')
            web_visit_norm = normalize_visit(web_visit_name)

            # Check if this is a target visit
            is_target = False
            for target in target_visits:
                if visit_matches(target, web_visit_name):
                    is_target = True
                    break

            if not is_target:
                continue

            # Check if already exists
            already_exists = False
            for existing_visit in existing_visits:
                if visit_matches(existing_visit, web_visit_name):
                    already_exists = True
                    break

            if already_exists:
                continue

            # Create new row
            new_row = {
                'study_name': study,
                'variable_name': variable,
                'variable_label': metadata.get('variable_label', template.get('variable_label', '')),
                'folder': metadata.get('folder', template.get('folder', '')),
                'description': metadata.get('description', template.get('description', '')),
                'visit': web_visit_name,
                'calculation': metadata.get('calculation', template.get('calculation', '')),
                'type': metadata.get('type', template.get('type', '')),
                'total_subjects': web_visit.get('total_subjects', ''),
                'units': metadata.get('units', template.get('units', '')),
                'n': web_visit.get('n', ''),
                'mean': web_visit.get('mean', ''),
                'stddev': web_visit.get('stddev', ''),
                'median': web_visit.get('median', ''),
                'min': web_visit.get('min', ''),
                'max': web_visit.get('max', ''),
                'unknown': web_visit.get('unknown', ''),
            }

            new_rows.append(new_row)
            existing_visits.add(web_visit_norm)  # Prevent duplicates

        time.sleep(RATE_LIMIT_DELAY)

    print(f"\nAdded {len(new_rows)} new rows")

    # Combine and sort
    all_rows = rows + new_rows

    # Sort by study, variable, visit
    all_rows.sort(key=lambda r: (r.get('study_name', ''), r.get('variable_name', ''), r.get('visit', '')))

    # Write output
    print(f"Writing {len(all_rows)} total rows to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_rows)

    print("Done!")

    # Summary by study
    print("\n=== Summary of new rows by study ===")
    for study in TARGET_VISITS.keys():
        study_new = [r for r in new_rows if r.get('study_name') == study]
        if study_new:
            visits = set(r.get('visit', '') for r in study_new)
            print(f"  {study}: {len(study_new)} new rows across {len(visits)} visits")
            for v in sorted(visits)[:3]:
                count = sum(1 for r in study_new if r.get('visit') == v)
                print(f"    - {v}: {count} rows")


if __name__ == "__main__":
    main()
