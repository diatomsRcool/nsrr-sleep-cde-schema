#!/usr/bin/env python3
"""
Test extraction script for MESA study only.
This is a verification run before full extraction.
"""

import csv
import time
import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime
from typing import Dict, List, Set, Optional

# Configuration
RATE_LIMIT_DELAY = 1.0
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# Files
CONTINUOUS_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'
CATEGORICAL_FILE = '/Users/athessen/sleep-cde-schema/categorical_variables_cde_updated.tsv'

class VariableExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def fetch_page(self, url: str, retry_count=0) -> Optional[BeautifulSoup]:
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            if retry_count < MAX_RETRIES:
                time.sleep(5)
                return self.fetch_page(url, retry_count + 1)
            else:
                print(f"  ERROR: Failed to fetch {url}: {e}")
                return None

    def get_all_variable_names(self, study: str) -> List[Dict]:
        """Fetch all variable names for a study"""
        variables = []
        page = 1

        while True:
            url = f"https://sleepdata.org/datasets/{study}/variables?page={page}"
            soup = self.fetch_page(url)

            if not soup:
                break

            found_on_page = 0
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                match = re.match(rf'/datasets/{study}/variables/([^/\?]+)$', href)
                if match:
                    var_name = match.group(1)
                    label = link.get_text(strip=True)

                    folder = ''
                    parent_row = link.find_parent('tr')
                    if parent_row:
                        cells = parent_row.find_all('td')
                        if len(cells) >= 3:
                            folder = cells[2].get_text(strip=True)

                    variables.append({
                        'variable_name': var_name,
                        'variable_label': label,
                        'folder': folder
                    })
                    found_on_page += 1

            print(f"  Page {page}: found {found_on_page} variables")

            if found_on_page == 0:
                break

            page += 1
            time.sleep(RATE_LIMIT_DELAY)

        return variables

    def extract_variable_metadata(self, study: str, variable: str) -> Dict:
        """Extract detailed metadata for a single variable"""
        url = f"https://sleepdata.org/datasets/{study}/variables/{variable}"
        soup = self.fetch_page(url)

        if not soup:
            return {}

        metadata = {
            'description': '',
            'type': '',
            'units': '',
            'domain': '',
            'calculation': ''
        }

        # Extract from form-groups
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            value_div = form_group.find('div', class_='form-control-plaintext')

            if not label_div or not value_div:
                continue

            label_text = label_div.get_text(strip=True).lower()
            value_text = value_div.get_text(strip=True)
            value_text = re.sub(r'\s+', ' ', value_text)

            if 'label' in label_text or 'description' in label_text:
                metadata['description'] = value_text
            elif 'type' in label_text:
                metadata['type'] = value_text
            elif 'unit' in label_text:
                metadata['units'] = value_text
            elif 'calculation' in label_text:
                metadata['calculation'] = value_text

        # Extract domain/choices
        domain_choices = []
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                match = re.match(r'^([0-9a-zA-Z\-]+)\s*[:\-]\s*(.+)$', text)
                if match:
                    code = match.group(1).strip()
                    label = match.group(2).strip()
                    domain_choices.append(f"{code}:{label}")

        if domain_choices:
            metadata['domain'] = '|'.join(domain_choices)

        # Extract statistics
        metadata['stats'] = self._extract_statistics(soup)

        return metadata

    def _extract_statistics(self, soup: BeautifulSoup) -> List[Dict]:
        stats_list = []

        for table in soup.find_all('table'):
            header_row = table.find('tr')
            if not header_row:
                continue

            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

            stats_headers = ['n', 'mean', 'median', 'min', 'max', 'std', 'stddev']
            if not any(h in headers for h in stats_headers):
                continue

            col_indices = {}
            for i, header in enumerate(headers):
                h = header.lower().strip()
                if h in ['n', 'count']:
                    col_indices['n'] = i
                elif h in ['mean', 'average']:
                    col_indices['mean'] = i
                elif h in ['std', 'stddev', 'std dev', 'stdev', 'sd']:
                    col_indices['stddev'] = i
                elif h == 'median':
                    col_indices['median'] = i
                elif h in ['min', 'minimum']:
                    col_indices['min'] = i
                elif h in ['max', 'maximum']:
                    col_indices['max'] = i
                elif h in ['unknown', 'missing']:
                    col_indices['unknown'] = i

            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= 1:
                    continue

                visit_name = cells[0].get_text(strip=True)

                skip_keywords = ['total', 'all', 'overall', 'male', 'female', 'treatment',
                                'white', 'black', 'asian', 'hispanic']
                if any(skip in visit_name.lower() for skip in skip_keywords):
                    continue

                visit_keywords = ['baseline', 'followup', 'follow-up', 'month', 'year',
                                 'visit', 'screening', 'week', 'v1', 'v2', 'v3', 'cycle', 'exam']
                if not any(kw in visit_name.lower() for kw in visit_keywords):
                    continue

                visit_stats = {'visit': visit_name}
                for stat_name, col_idx in col_indices.items():
                    if col_idx < len(cells):
                        value = cells[col_idx].get_text(strip=True)
                        value = re.sub(r'[^\d.\-]', '', value)
                        visit_stats[stat_name] = value

                stats_list.append(visit_stats)

        return stats_list


def load_existing_variables(study: str) -> Set[str]:
    """Load existing variable names for a study"""
    existing = set()

    for file_path in [CONTINUOUS_FILE, CATEGORICAL_FILE]:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    if row['study_name'].lower() == study.lower():
                        existing.add(row['variable_name'])

    return existing


def main():
    study = 'mesa'
    print(f"=" * 60)
    print(f"TEST EXTRACTION: {study.upper()}")
    print(f"=" * 60)

    extractor = VariableExtractor()

    # Load existing variables
    existing = load_existing_variables(study)
    print(f"Existing variables: {len(existing)}")

    # Get all variable names
    print(f"\nFetching all variable names from sleepdata.org...")
    all_vars = extractor.get_all_variable_names(study)
    print(f"Total variables found: {len(all_vars)}")

    # Find missing
    missing_vars = [v for v in all_vars if v['variable_name'] not in existing]
    print(f"Missing variables: {len(missing_vars)}")

    if not missing_vars:
        print("No missing variables to extract!")
        return

    # Estimate time
    est_minutes = len(missing_vars) * RATE_LIMIT_DELAY / 60
    print(f"Estimated extraction time: {est_minutes:.1f} minutes")
    print(f"\nStarting extraction...")

    # Process missing variables
    new_continuous = []
    new_categorical = []

    continuous_fieldnames = ['study_name', 'variable_name', 'variable_label', 'folder',
                            'description', 'visit', 'calculation', 'type', 'total_subjects',
                            'units', 'n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown']
    categorical_fieldnames = ['study_name', 'variable_name', 'variable_label', 'folder',
                             'description', 'domain', 'type']

    start_time = datetime.now()

    for i, var in enumerate(missing_vars):
        var_name = var['variable_name']

        if (i + 1) % 25 == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(missing_vars) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(missing_vars)}] {var_name} (ETA: {remaining/60:.1f} min)")

        metadata = extractor.extract_variable_metadata(study, var_name)
        time.sleep(RATE_LIMIT_DELAY)

        if not metadata:
            continue

        # Determine if continuous or categorical
        var_type = metadata.get('type', '').lower()
        has_domain = bool(metadata.get('domain'))

        is_categorical = (
            'choice' in var_type or
            'identifier' in var_type or
            has_domain or
            var_type in ['string', 'text']
        )

        if is_categorical:
            row = {
                'study_name': study.upper(),
                'variable_name': var_name,
                'variable_label': var.get('variable_label', ''),
                'folder': var.get('folder', ''),
                'description': metadata.get('description', ''),
                'domain': metadata.get('domain', ''),
                'type': metadata.get('type', '')
            }
            new_categorical.append(row)
        else:
            stats = metadata.get('stats', [{}])
            if not stats:
                stats = [{}]

            for stat in stats:
                row = {
                    'study_name': study.upper(),
                    'variable_name': var_name,
                    'variable_label': var.get('variable_label', ''),
                    'folder': var.get('folder', ''),
                    'description': metadata.get('description', ''),
                    'visit': stat.get('visit', ''),
                    'calculation': metadata.get('calculation', ''),
                    'type': metadata.get('type', 'numeric'),
                    'total_subjects': '',
                    'units': metadata.get('units', ''),
                    'n': stat.get('n', ''),
                    'mean': stat.get('mean', ''),
                    'stddev': stat.get('stddev', ''),
                    'median': stat.get('median', ''),
                    'min': stat.get('min', ''),
                    'max': stat.get('max', ''),
                    'unknown': stat.get('unknown', '')
                }
                new_continuous.append(row)

    # Append to files
    print(f"\nWriting results...")

    if new_continuous:
        with open(CONTINUOUS_FILE, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=continuous_fieldnames, delimiter='\t')
            writer.writerows(new_continuous)
        print(f"  Added {len(new_continuous)} continuous variable rows")

    if new_categorical:
        with open(CATEGORICAL_FILE, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=categorical_fieldnames, delimiter='\t')
            writer.writerows(new_categorical)
        print(f"  Added {len(new_categorical)} categorical variable rows")

    elapsed = datetime.now() - start_time
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"Time: {elapsed}")
    print(f"New continuous rows: {len(new_continuous)}")
    print(f"New categorical rows: {len(new_categorical)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
