#!/usr/bin/env python3
"""
Update missing statistics for specific study/visit combinations.
"""

import csv
import time
import requests
from bs4 import BeautifulSoup
import re
import sys
from typing import Dict, List, Optional

# Configuration
RATE_LIMIT_DELAY = 1.0
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

INPUT_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'
OUTPUT_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'

# Target study/visit combinations
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
    # All visits for these studies
    'MESA': None,  # None means all visits
    'MSP': None,
    'STAGES': None,
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

    def extract_all_visit_stats(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """Extract statistics for ALL visits from the page."""
        if not soup:
            return {}

        visit_stats = {}

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
                elif header_clean in ['total']:
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
                stats = {}
                for stat_name, col_idx in col_indices.items():
                    if col_idx < len(cells):
                        value = cells[col_idx].get_text(strip=True)
                        # Clean up value
                        value = value.replace('±', '').replace('\u00b1', '').strip()
                        if value and value != '-' and value != '—':
                            stats[stat_name] = value

                if stats:
                    visit_stats[visit_name] = stats

        return visit_stats


def normalize_visit_name(visit: str) -> str:
    """Normalize visit name for matching."""
    return visit.lower().strip()


def match_visit(target_visit: str, available_visits: Dict) -> Optional[str]:
    """Find the best matching visit from available visits."""
    target_norm = normalize_visit_name(target_visit)

    # First try exact match
    for visit in available_visits:
        if normalize_visit_name(visit) == target_norm:
            return visit

    # Try partial match
    for visit in available_visits:
        visit_norm = normalize_visit_name(visit)
        # Check if one contains the other
        if target_norm in visit_norm or visit_norm in target_norm:
            return visit
        # Check key parts match
        target_parts = set(re.split(r'[\s\-_/()]+', target_norm))
        visit_parts = set(re.split(r'[\s\-_/()]+', visit_norm))
        if len(target_parts & visit_parts) >= 2:
            return visit

    return None


def needs_stats(row: Dict) -> bool:
    """Check if a row needs statistics."""
    n = row.get('n', '').strip()
    mean = row.get('mean', '').strip()
    return n in ['', '-', '—'] or mean in ['', '-', '—']


def should_update(study: str, visit: str) -> bool:
    """Check if this study/visit combination should be updated."""
    if study not in TARGET_VISITS:
        return False

    target_visits = TARGET_VISITS[study]
    if target_visits is None:  # All visits for this study
        return True

    # Check if visit matches any target
    visit_norm = normalize_visit_name(visit)
    for target in target_visits:
        target_norm = normalize_visit_name(target)
        if target_norm == visit_norm or target_norm in visit_norm or visit_norm in target_norm:
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

    # Identify unique study/variable combinations needing updates
    vars_to_fetch = set()
    for row in rows:
        study = row.get('study_name', '')
        variable = row.get('variable_name', '')
        visit = row.get('visit', '')

        if should_update(study, visit) and needs_stats(row):
            vars_to_fetch.add((study, variable))

    print(f"Found {len(vars_to_fetch)} unique study/variable combinations to fetch")

    # Fetch statistics
    parser = VariablePageParser()
    stats_cache = {}  # Cache: (study, variable) -> {visit: stats}

    fetched = 0
    for study, variable in sorted(vars_to_fetch):
        fetched += 1
        if fetched % 10 == 0 or fetched <= 5:
            print(f"[{fetched}/{len(vars_to_fetch)}] Fetching {study}/{variable}...")

        soup = parser.fetch_page(study, variable)
        if soup:
            visit_stats = parser.extract_all_visit_stats(soup)
            stats_cache[(study, variable)] = visit_stats
        else:
            stats_cache[(study, variable)] = {}

        time.sleep(RATE_LIMIT_DELAY)

    # Update rows
    updated_count = 0
    for row in rows:
        study = row.get('study_name', '')
        variable = row.get('variable_name', '')
        visit = row.get('visit', '')

        if not should_update(study, visit):
            continue

        if not needs_stats(row):
            continue

        # Get cached stats
        visit_stats = stats_cache.get((study, variable), {})
        if not visit_stats:
            continue

        # Find matching visit
        matched_visit = match_visit(visit, visit_stats)
        if not matched_visit:
            continue

        stats = visit_stats[matched_visit]

        # Update row with stats (only if empty or '-')
        updated = False
        for stat_key in ['n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown', 'total_subjects']:
            if stat_key in stats:
                current = row.get(stat_key, '').strip()
                if current in ['', '-', '—']:
                    row[stat_key] = stats[stat_key]
                    updated = True

        if updated:
            updated_count += 1

    print(f"\nUpdated {updated_count} rows")

    # Write output
    print(f"Writing output to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)

    print("Done!")


if __name__ == "__main__":
    main()
