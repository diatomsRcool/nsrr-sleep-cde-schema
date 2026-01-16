#!/usr/bin/env python3
"""
Update missing descriptions in categorical_variables_cde.txt

Fetches descriptions from sleepdata.org variable pages.
Only updates empty description fields - does not overwrite existing data.
"""

import csv
import time
import requests
from bs4 import BeautifulSoup
import re
import sys
from typing import Dict, Optional

# Configuration
RATE_LIMIT_DELAY = 1.0
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

INPUT_FILE = '/Users/athessen/sleep-cde-schema/categorical_variables_cde.txt'
OUTPUT_FILE = '/Users/athessen/sleep-cde-schema/categorical_variables_cde_updated.tsv'


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

    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extract description from the variable page."""
        if not soup:
            return ""

        # Strategy 1: Look for form-group with "Description" label
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div:
                label_text = label_div.get_text(strip=True).lower()
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


def main():
    print(f"Reading input file: {INPUT_FILE}")

    # Read all rows
    rows = []
    with open(INPUT_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        headers = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Clean up headers (remove empty ones)
    headers = [h for h in headers if h and h.strip()]

    print(f"Found {len(rows)} rows")
    print(f"Headers: {headers}")

    # Count missing descriptions
    missing_desc = [(i, r) for i, r in enumerate(rows) if not r.get('description', '').strip()]
    print(f"Rows with missing descriptions: {len(missing_desc)}")

    # Get unique study/variable combinations with missing descriptions
    vars_to_fetch = set()
    for i, row in missing_desc:
        study = row.get('study_name', '')
        variable = row.get('variable_name', '')
        if study and variable:
            vars_to_fetch.add((study, variable))

    print(f"Unique study/variable combinations to fetch: {len(vars_to_fetch)}")

    # Fetch descriptions
    parser = VariablePageParser()
    descriptions = {}  # (study, variable) -> description

    fetched = 0
    for study, variable in sorted(vars_to_fetch):
        fetched += 1
        if fetched % 50 == 0 or fetched <= 5:
            print(f"[{fetched}/{len(vars_to_fetch)}] Fetching {study}/{variable}...")

        soup = parser.fetch_page(study, variable)
        if soup:
            desc = parser.extract_description(soup)
            if desc:
                descriptions[(study, variable)] = desc

        time.sleep(RATE_LIMIT_DELAY)

    print(f"\nFetched {len(descriptions)} descriptions")

    # Update rows
    updated_count = 0
    for row in rows:
        study = row.get('study_name', '')
        variable = row.get('variable_name', '')
        current_desc = row.get('description', '').strip()

        # Only update if description is empty
        if not current_desc:
            key = (study, variable)
            if key in descriptions:
                row['description'] = descriptions[key]
                updated_count += 1

    print(f"Updated {updated_count} descriptions")

    # Write output
    print(f"\nWriting output to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    print("Done!")

    # Summary by study
    print("\n=== Summary by study ===")
    study_counts = {}
    for row in rows:
        study = row.get('study_name', '')
        if study not in study_counts:
            study_counts[study] = {'total': 0, 'with_desc': 0}
        study_counts[study]['total'] += 1
        if row.get('description', '').strip():
            study_counts[study]['with_desc'] += 1

    for study in sorted(study_counts.keys()):
        data = study_counts[study]
        pct = data['with_desc'] * 100 // data['total'] if data['total'] > 0 else 0
        print(f"  {study}: {data['with_desc']}/{data['total']} ({pct}%) have descriptions")


if __name__ == "__main__":
    main()
