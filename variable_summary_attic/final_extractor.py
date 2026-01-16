#!/usr/bin/env python3
"""
Final comprehensive extractor for all 31 sleep studies
Extracts variable lists and basic metadata
Note: Detailed statistics (n, mean, stddev, etc.) for each variable
would require visiting thousands of individual pages
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import json
import re
from typing import List, Dict

STUDIES = [
    'abc', 'answers', 'apoe', 'apples', 'bestair', 'ccshs', 'cfs', 'chat',
    'disecad', 'fdcsr', 'ffcws', 'haassa', 'hchs', 'heartbeat', 'homepap',
    'isaps', 'lofthf', 'mesa', 'mros', 'msp', 'nchsdb', 'nfs', 'numom2b',
    'pats', 'pimecfs', 'sandd', 'shine', 'shhs', 'sof', 'stages', 'wsc'
]

BASE_URL = "https://sleepdata.org"

def classify_variable(var_type: str, var_name: str) -> str:
    """Classify variable as continuous or categorical"""
    if not var_type:
        return 'continuous'

    var_type_lower = var_type.lower()
    var_name_lower = var_name.lower()

    # Continuous types
    if any(t in var_type_lower for t in ['numeric', 'integer', 'float', 'continuous']):
        return 'continuous'

    # Categorical types
    if any(t in var_type_lower for t in ['categorical', 'choice', 'binary', 'enumeration', 'identifier', 'ordinal', 'date', 'time']):
        return 'categorical'

    # Check variable name
    if any(x in var_name_lower for x in ['_id', 'id$', 'date', 'time']):
        return 'categorical'

    return 'continuous'

def extract_variables_from_page(html_content: str) -> List[Dict]:
    """Extract variables from HTML page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    variables = []

    # Strategy 1: Look for variable tables
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 2:
                # Try to find variable links
                link = row.find('a', href=re.compile(r'/variables/'))
                if link:
                    var_name = link.get_text(strip=True)
                    var_label = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                    var_type = cols[2].get_text(strip=True) if len(cols) > 2 else ''
                    folder = cols[3].get_text(strip=True) if len(cols) > 3 else ''

                    if var_name:
                        variables.append({
                            'variable_name': var_name,
                            'variable_label': var_label,
                            'type': var_type,
                            'folder': folder
                        })

    # Strategy 2: Look for variable links
    if not variables:
        links = soup.find_all('a', href=re.compile(r'/variables/[^/]+$'))
        for link in links:
            var_name = link.get_text(strip=True)
            if var_name and not var_name.startswith('?'):
                # Try to find associated metadata
                parent = link.find_parent(['tr', 'div', 'li'])
                var_label = ''
                var_type = ''

                if parent:
                    text = parent.get_text()
                    # Try to extract label and type from surrounding text
                    pass

                variables.append({
                    'variable_name': var_name,
                    'variable_label': var_label,
                    'type': var_type,
                    'folder': ''
                })

    # Remove duplicates
    seen = set()
    unique_vars = []
    for var in variables:
        key = var['variable_name']
        if key and key not in seen:
            seen.add(key)
            unique_vars.append(var)

    return unique_vars

def extract_study(study_id: str, session: requests.Session) -> List[Dict]:
    """Extract all variables from a study"""
    url = f"{BASE_URL}/datasets/{study_id}/variables"
    print(f"  Fetching {url}")

    try:
        response = session.get(url, timeout=30)
        if response.status_code != 200:
            print(f"    Error: HTTP {response.status_code}")
            return []

        variables = extract_variables_from_page(response.text)
        print(f"    Found {len(variables)} variables")
        return variables

    except Exception as e:
        print(f"    Error: {e}")
        return []

def main():
    """Main extraction function"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    all_continuous = []
    all_categorical = []

    for i, study in enumerate(STUDIES, 1):
        print(f"\n[{i}/{len(STUDIES)}] Processing {study.upper()}...")

        variables = extract_study(study, session)

        for var in variables:
            classification = classify_variable(var.get('type', ''), var.get('variable_name', ''))

            base_data = {
                'study_name': study.upper(),
                'variable_name': var.get('variable_name', ''),
                'variable_label': var.get('variable_label', ''),
                'folder': var.get('folder', ''),
                'description': '',
                'visit': '',
                'domain': '',
                'type': var.get('type', '')
            }

            if classification == 'continuous':
                all_continuous.append({
                    **base_data,
                    'total_subjects': '',
                    'units': '',
                    'n': '',
                    'mean': '',
                    'stddev': '',
                    'median': '',
                    'min': '',
                    'max': '',
                    'unknown': ''
                })
            else:
                all_categorical.append(base_data)

        # Rate limiting
        time.sleep(1)

    # Write continuous variables
    continuous_file = '/Users/athessen/sleep-cde-schema/continuous_variables.tsv'
    with open(continuous_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['study_name', 'variable_name', 'variable_label', 'folder',
                     'description', 'visit', 'domain', 'type', 'total_subjects',
                     'units', 'n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown']
        writer = csv.DictWriter(f, delimiter='\t', fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_continuous)

    print(f"\nWrote {len(all_continuous)} continuous variables to {continuous_file}")

    # Write categorical variables
    categorical_file = '/Users/athessen/sleep-cde-schema/categorical_variables.tsv'
    with open(categorical_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['study_name', 'variable_name', 'variable_label', 'folder',
                     'description', 'visit', 'domain', 'type']
        writer = csv.DictWriter(f, delimiter='\t', fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_categorical)

    print(f"Wrote {len(all_categorical)} categorical variables to {categorical_file}")

    # Summary by study
    print("\n" + "="*80)
    print("SUMMARY BY STUDY")
    print("="*80)

    from collections import defaultdict
    cont_by_study = defaultdict(int)
    cat_by_study = defaultdict(int)

    for var in all_continuous:
        cont_by_study[var['study_name']] += 1

    for var in all_categorical:
        cat_by_study[var['study_name']] += 1

    all_studies = sorted(set(list(cont_by_study.keys()) + list(cat_by_study.keys())))
    for study in all_studies:
        cont = cont_by_study[study]
        cat = cat_by_study[study]
        print(f"{study:12} {cont:4} continuous + {cat:4} categorical = {cont+cat:4} total")

    print(f"\nGRAND TOTAL: {len(all_continuous)} continuous + {len(all_categorical)} categorical = {len(all_continuous) + len(all_categorical)} total")

if __name__ == '__main__':
    main()
