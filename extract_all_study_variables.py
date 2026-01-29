#!/usr/bin/env python3
"""
Complete NSRR Variable Extraction Script

This script extracts ALL variables from each of the 31 NSRR studies on sleepdata.org,
compares against currently extracted variables, and adds missing ones.

Features:
- Paginated fetching of all variable names per study
- Comparison against existing TSV files
- Metadata extraction for missing variables
- Rate limiting and retry logic
- Progress tracking and resumability
"""

import csv
import time
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional

# Configuration
RATE_LIMIT_DELAY = 1.0  # seconds between requests
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5
VARIABLES_PER_PAGE = 100

# Studies to process (31 studies already in the TSV files)
# Studies to process - MESA already completed in test run
STUDIES = [
    'abc', 'answers', 'apoe', 'apples', 'bestair', 'ccshs', 'cfs', 'chat',
    'disecad', 'fdcsr', 'ffcws', 'haassa', 'hchs', 'heartbeat', 'homepap',
    'isaps', 'lofthf', 'mros', 'msp', 'nchsdb', 'nfs', 'numom2b',
    'pats', 'pimecfs', 'sandd', 'shine', 'shhs', 'sof', 'stages', 'wsc'
]
# Note: 'mesa' removed - already extracted in test run

# File paths
CONTINUOUS_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'
CATEGORICAL_FILE = '/Users/athessen/sleep-cde-schema/categorical_variables_cde_updated.tsv'
PROGRESS_FILE = '/Users/athessen/sleep-cde-schema/extraction_progress.json'
LOG_FILE = '/Users/athessen/sleep-cde-schema/full_extraction_log.txt'

class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
        with open(self.log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Extraction started: {datetime.now()}\n")
            f.write(f"{'='*80}\n\n")

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")


class VariableExtractor:
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def fetch_page(self, url: str, retry_count=0) -> Optional[BeautifulSoup]:
        """Fetch and parse a page with retry logic"""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.fetch_page(url, retry_count + 1)
            else:
                self.logger.log(f"Failed to fetch {url}: {e}", "ERROR")
                return None

    def get_total_variables(self, study: str) -> int:
        """Get total number of variables for a study"""
        url = f"https://sleepdata.org/datasets/{study}/variables"
        soup = self.fetch_page(url)
        if not soup:
            return 0

        # Look for pagination info like "1 to 100 of 1,848"
        text = soup.get_text()
        match = re.search(r'of\s+([\d,]+)', text)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0

    def get_all_variable_names(self, study: str) -> List[Dict]:
        """Fetch all variable names and basic info for a study"""
        variables = []
        page = 1

        total = self.get_total_variables(study)
        self.logger.log(f"  {study.upper()}: {total} total variables")

        if total == 0:
            return variables

        total_pages = (total // VARIABLES_PER_PAGE) + 1

        while True:
            url = f"https://sleepdata.org/datasets/{study}/variables?page={page}"
            soup = self.fetch_page(url)

            if not soup:
                break

            # Find variable rows in the table
            found_on_page = 0

            # Try to find links to variable pages
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Match pattern like /datasets/shhs/variables/varname
                match = re.match(rf'/datasets/{study}/variables/([^/\?]+)$', href)
                if match:
                    var_name = match.group(1)
                    # Get the label (link text)
                    label = link.get_text(strip=True)

                    # Try to find folder from parent row
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

            self.logger.log(f"    Page {page}/{total_pages}: found {found_on_page} variables")

            if found_on_page == 0 or page >= total_pages:
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
            'calculation': '',
            'commonly_used': False
        }

        # Extract from form-groups (common NSRR page structure)
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
            elif 'commonly used' in label_text:
                metadata['commonly_used'] = 'yes' in value_text.lower()

        # Extract domain/choices for categorical variables
        domain_choices = []
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                # Match "code: label" pattern
                match = re.match(r'^([0-9a-zA-Z\-]+)\s*[:\-]\s*(.+)$', text)
                if match:
                    code = match.group(1).strip()
                    label = match.group(2).strip()
                    domain_choices.append(f"{code}:{label}")

        if domain_choices:
            metadata['domain'] = '|'.join(domain_choices)

        # Extract statistics if present
        metadata['stats'] = self._extract_statistics(soup)

        return metadata

    def _extract_statistics(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract statistics tables (for continuous variables)"""
        stats_list = []

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

            # Extract data rows
            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= 1:
                    continue

                visit_name = cells[0].get_text(strip=True)

                # Skip totals and demographic breakdowns
                skip_keywords = ['total', 'all', 'overall', 'male', 'female', 'treatment',
                                'white', 'black', 'asian', 'hispanic']
                if any(skip in visit_name.lower() for skip in skip_keywords):
                    continue

                # Only include visit-like rows
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


def load_existing_variables() -> Tuple[Set[str], Set[str]]:
    """Load existing variable names from TSV files"""
    continuous_vars = set()
    categorical_vars = set()

    # Load continuous variables
    if os.path.exists(CONTINUOUS_FILE):
        with open(CONTINUOUS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                key = f"{row['study_name'].lower()}|{row['variable_name']}"
                continuous_vars.add(key)

    # Load categorical variables
    if os.path.exists(CATEGORICAL_FILE):
        with open(CATEGORICAL_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                key = f"{row['study_name'].lower()}|{row['variable_name']}"
                categorical_vars.add(key)

    return continuous_vars, categorical_vars


def save_progress(progress: Dict):
    """Save extraction progress for resumability"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def load_progress() -> Dict:
    """Load extraction progress"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed_studies': [], 'current_study': None, 'current_index': 0}


def append_to_tsv(file_path: str, rows: List[Dict], fieldnames: List[str]):
    """Append rows to a TSV file"""
    file_exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0

    with open(file_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main():
    logger = Logger(LOG_FILE)
    extractor = VariableExtractor(logger)

    logger.log("Loading existing variables from TSV files...")
    continuous_vars, categorical_vars = load_existing_variables()
    all_existing = continuous_vars | categorical_vars
    logger.log(f"Found {len(continuous_vars)} continuous and {len(categorical_vars)} categorical variables")

    # Load progress
    progress = load_progress()

    # Define fieldnames for output
    continuous_fieldnames = ['study_name', 'variable_name', 'variable_label', 'folder',
                            'description', 'visit', 'calculation', 'type', 'total_subjects',
                            'units', 'n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown']
    categorical_fieldnames = ['study_name', 'variable_name', 'variable_label', 'folder',
                             'description', 'domain', 'type']

    total_new_vars = 0

    for study in STUDIES:
        if study in progress.get('completed_studies', []):
            logger.log(f"Skipping {study.upper()} (already completed)")
            continue

        logger.log(f"\n{'='*60}")
        logger.log(f"Processing study: {study.upper()}")
        logger.log(f"{'='*60}")

        # Get all variable names for this study
        all_vars = extractor.get_all_variable_names(study)
        logger.log(f"Found {len(all_vars)} total variables")
        time.sleep(RATE_LIMIT_DELAY)

        # Filter to only missing variables
        missing_vars = []
        for var in all_vars:
            key = f"{study}|{var['variable_name']}"
            if key not in all_existing:
                missing_vars.append(var)

        logger.log(f"Missing variables: {len(missing_vars)}")

        if not missing_vars:
            progress['completed_studies'].append(study)
            save_progress(progress)
            continue

        # Process missing variables
        new_continuous = []
        new_categorical = []

        start_idx = progress.get('current_index', 0) if progress.get('current_study') == study else 0

        for i, var in enumerate(missing_vars[start_idx:], start=start_idx):
            var_name = var['variable_name']

            if (i + 1) % 10 == 0:
                logger.log(f"  [{i+1}/{len(missing_vars)}] Processing {var_name}...")

            # Extract metadata
            metadata = extractor.extract_variable_metadata(study, var_name)
            time.sleep(RATE_LIMIT_DELAY)

            if not metadata:
                continue

            # Determine if continuous or categorical
            var_type = metadata.get('type', '').lower()
            has_domain = bool(metadata.get('domain'))
            has_stats = bool(metadata.get('stats'))

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
                # Continuous - may have multiple rows for different visits
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

            # Save progress periodically
            if (i + 1) % 50 == 0:
                progress['current_study'] = study
                progress['current_index'] = i + 1
                save_progress(progress)

                # Also append accumulated rows
                if new_continuous:
                    append_to_tsv(CONTINUOUS_FILE, new_continuous, continuous_fieldnames)
                    total_new_vars += len(new_continuous)
                    new_continuous = []
                if new_categorical:
                    append_to_tsv(CATEGORICAL_FILE, new_categorical, categorical_fieldnames)
                    total_new_vars += len(new_categorical)
                    new_categorical = []

                logger.log(f"  Progress saved. Total new variables so far: {total_new_vars}")

        # Append remaining rows for this study
        if new_continuous:
            append_to_tsv(CONTINUOUS_FILE, new_continuous, continuous_fieldnames)
            total_new_vars += len(new_continuous)
        if new_categorical:
            append_to_tsv(CATEGORICAL_FILE, new_categorical, categorical_fieldnames)
            total_new_vars += len(new_categorical)

        # Mark study as completed
        progress['completed_studies'].append(study)
        progress['current_study'] = None
        progress['current_index'] = 0
        save_progress(progress)

        logger.log(f"Completed {study.upper()}. Total new variables: {total_new_vars}")

    logger.log(f"\n{'='*60}")
    logger.log(f"EXTRACTION COMPLETE")
    logger.log(f"Total new variables added: {total_new_vars}")
    logger.log(f"{'='*60}")


if __name__ == "__main__":
    main()
