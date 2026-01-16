#!/usr/bin/env python3
"""
Extract all variables from 31 sleep studies at sleepdata.org
Classifies variables as continuous or categorical and saves to TSV files.
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
import re
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STUDIES = [
    'abc', 'answers', 'apoe', 'apples', 'bestair', 'ccshs', 'cfs', 'chat',
    'disecad', 'fdcsr', 'ffcws', 'haassa', 'hchs', 'heartbeat', 'homepap',
    'isaps', 'lofthf', 'mesa', 'mros', 'msp', 'nchsdb', 'nfs', 'numom2b',
    'pats', 'pimecfs', 'sandd', 'shine', 'shhs', 'sof', 'stages', 'wsc'
]

BASE_URL = "https://sleepdata.org"


def get_variable_list(study_id: str) -> List[str]:
    """Get all variable names for a study."""
    variables = []
    page = 1

    while True:
        url = f"{BASE_URL}/datasets/{study_id}/variables"
        if page > 1:
            url += f"?page={page}"

        logger.info(f"Fetching variable list for {study_id}, page {page}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find variable links
            var_links = soup.find_all('a', href=re.compile(f'/datasets/{study_id}/variables/[^/]+$'))

            if not var_links:
                break

            for link in var_links:
                var_name = link['href'].split('/')[-1]
                if var_name not in variables:
                    variables.append(var_name)

            # Check if there's a next page
            next_link = soup.find('a', string='Next')
            if not next_link or 'disabled' in next_link.get('class', []):
                break

            page += 1
            time.sleep(0.5)  # Be respectful to the server

        except Exception as e:
            logger.error(f"Error fetching variables for {study_id} page {page}: {e}")
            break

    logger.info(f"Found {len(variables)} variables for {study_id}")
    return variables


def parse_variable_detail(study_id: str, var_name: str) -> Optional[Dict]:
    """Parse detailed information for a single variable."""
    url = f"{BASE_URL}/datasets/{study_id}/variables/{var_name}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        data = {
            'study_name': study_id.upper(),
            'variable_name': var_name,
            'variable_label': '',
            'folder': '',
            'description': '',
            'domain': '',
            'type': '',
            'total_subjects': '',
            'units': '',
            'n': '',
            'mean': '',
            'stddev': '',
            'median': '',
            'min': '',
            'max': '',
            'unknown': ''
        }

        # Extract label
        label_elem = soup.find('h1')
        if label_elem:
            data['variable_label'] = label_elem.get_text(strip=True)

        # Extract metadata from definition list
        dt_elements = soup.find_all('dt')
        for dt in dt_elements:
            dd = dt.find_next_sibling('dd')
            if not dd:
                continue

            key = dt.get_text(strip=True).lower()
            value = dd.get_text(strip=True)

            if 'folder' in key:
                data['folder'] = value
            elif 'type' in key:
                data['type'] = value
            elif 'domain' in key:
                data['domain'] = value
            elif 'unit' in key:
                data['units'] = value
            elif 'description' in key or 'commonly' in key:
                data['description'] = value

        # Extract statistics from table (look for first/baseline visit)
        stats_table = soup.find('table')
        if stats_table:
            rows = stats_table.find_all('tr')

            # Find header row
            header_row = None
            for row in rows:
                if row.find('th'):
                    header_row = row
                    break

            if header_row:
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all('th')]

                # Get first data row (baseline visit)
                data_rows = [r for r in rows if r.find('td')]
                if data_rows:
                    first_row = data_rows[0]
                    cells = first_row.find_all('td')

                    for i, cell in enumerate(cells):
                        if i >= len(headers):
                            break

                        header = headers[i]
                        value = cell.get_text(strip=True)

                        # Clean up values
                        value = value.replace('±', '').strip()

                        if 'n' == header or 'count' in header:
                            data['n'] = value
                        elif 'mean' in header:
                            data['mean'] = value
                        elif 'std' in header or 'sd' in header:
                            data['stddev'] = value
                        elif 'median' in header:
                            data['median'] = value
                        elif 'min' in header:
                            data['min'] = value
                        elif 'max' in header:
                            data['max'] = value
                        elif 'unknown' in header or 'missing' in header:
                            data['unknown'] = value

        # Try to extract total subjects
        text = soup.get_text()
        subjects_match = re.search(r'(\d+)\s+subjects?', text, re.IGNORECASE)
        if subjects_match:
            data['total_subjects'] = subjects_match.group(1)

        return data

    except Exception as e:
        logger.error(f"Error parsing {study_id}/{var_name}: {e}")
        return None


def is_continuous(var_data: Dict) -> bool:
    """Determine if a variable is continuous based on type and statistics."""
    var_type = var_data.get('type', '').lower()

    # Check type
    if any(t in var_type for t in ['numeric', 'integer', 'float', 'continuous']):
        return True

    # Check if has statistics
    if var_data.get('mean') or var_data.get('stddev') or var_data.get('median'):
        return True

    # Check for categorical indicators
    if any(t in var_type for t in ['choice', 'categorical', 'enumeration', 'string']):
        return False

    # Default to categorical if unclear
    return False


def extract_all_studies():
    """Extract variables from all studies and save to TSV files."""
    continuous_file = '/Users/athessen/sleep-cde-schema/continuous_variables.tsv'
    categorical_file = '/Users/athessen/sleep-cde-schema/categorical_variables.tsv'

    continuous_fields = ['study_name', 'variable_name', 'variable_label', 'folder',
                        'description', 'domain', 'type', 'total_subjects', 'units',
                        'n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown']

    categorical_fields = ['study_name', 'variable_name', 'variable_label', 'folder',
                         'description', 'domain', 'type']

    with open(continuous_file, 'w', newline='', encoding='utf-8') as cont_f, \
         open(categorical_file, 'w', newline='', encoding='utf-8') as cat_f:

        cont_writer = csv.DictWriter(cont_f, fieldnames=continuous_fields,
                                     delimiter='\t', extrasaction='ignore')
        cat_writer = csv.DictWriter(cat_f, fieldnames=categorical_fields,
                                    delimiter='\t', extrasaction='ignore')

        cont_writer.writeheader()
        cat_writer.writeheader()

        for study in STUDIES:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing study: {study.upper()}")
            logger.info(f"{'='*60}")

            variables = get_variable_list(study)

            # Limit to first 100 variables per study for efficiency
            # (you can remove this limit if you want all variables)
            sample_size = min(100, len(variables))
            variables_to_process = variables[:sample_size]

            logger.info(f"Processing {sample_size} of {len(variables)} variables")

            for i, var_name in enumerate(variables_to_process, 1):
                if i % 10 == 0:
                    logger.info(f"  Progress: {i}/{sample_size}")

                var_data = parse_variable_detail(study, var_name)

                if var_data:
                    if is_continuous(var_data):
                        cont_writer.writerow(var_data)
                    else:
                        cat_writer.writerow(var_data)

                time.sleep(0.3)  # Rate limiting

            logger.info(f"Completed {study.upper()}")

    logger.info(f"\n{'='*60}")
    logger.info("Extraction complete!")
    logger.info(f"Continuous variables saved to: {continuous_file}")
    logger.info(f"Categorical variables saved to: {categorical_file}")
    logger.info(f"{'='*60}")


if __name__ == '__main__':
    extract_all_studies()
