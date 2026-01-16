#!/usr/bin/env python3
"""
Comprehensive variable extraction script for 31 sleep studies from sleepdata.org
Handles multi-visit data properly by creating separate rows for each visit.
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
import re
from typing import Dict, List, Tuple, Optional
import sys

# List of all 31 studies
STUDIES = [
    'abc', 'answers', 'apoe', 'apples', 'bestair', 'ccshs', 'cfs', 'chat',
    'disecad', 'fdcsr', 'ffcws', 'haassa', 'hchs', 'heartbeat', 'homepap',
    'isaps', 'lofthf', 'mesa', 'mros', 'msp', 'nchsdb', 'nfs', 'numom2b',
    'pats', 'pimecfs', 'sandd', 'shine', 'shhs', 'sof', 'stages', 'wsc'
]

BASE_URL = "https://sleepdata.org"

class VariableExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.continuous_vars = []
        self.categorical_vars = []

    def extract_all_studies(self):
        """Extract variables from all 31 studies"""
        for study in STUDIES:
            print(f"\n{'='*80}")
            print(f"Processing study: {study.upper()}")
            print(f"{'='*80}")
            try:
                self.extract_study(study)
                time.sleep(2)  # Be respectful with rate limiting
            except Exception as e:
                print(f"ERROR processing {study}: {e}")
                continue

    def extract_study(self, study_id: str):
        """Extract all variables from a single study"""
        # Get variable list page
        vars_url = f"{BASE_URL}/datasets/{study_id}/variables"
        print(f"Fetching variables list from: {vars_url}")

        response = self.session.get(vars_url)
        if response.status_code != 200:
            print(f"Failed to fetch {vars_url}: {response.status_code}")
            return

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all variable links
        variable_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if f'/datasets/{study_id}/variables/' in href and href.count('/') == 4:
                var_name = href.split('/')[-1]
                if var_name and not var_name.startswith('?'):
                    variable_links.append(var_name)

        # Remove duplicates and sort
        variable_links = sorted(list(set(variable_links)))
        print(f"Found {len(variable_links)} variables")

        # Extract each variable
        for i, var_name in enumerate(variable_links, 1):
            print(f"  [{i}/{len(variable_links)}] Extracting {var_name}...", end=' ')
            try:
                self.extract_variable(study_id, var_name)
                print("✓")
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"✗ Error: {e}")
                continue

    def extract_variable(self, study_id: str, var_name: str):
        """Extract detailed information for a single variable"""
        var_url = f"{BASE_URL}/datasets/{study_id}/variables/{var_name}"

        response = self.session.get(var_url)
        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract basic metadata
        var_label = self.extract_text(soup, 'Variable Label')
        folder = self.extract_text(soup, 'Folder') or self.extract_text(soup, 'Domain')
        description = self.extract_text(soup, 'Description')
        var_type = self.extract_text(soup, 'Type')
        units = self.extract_text(soup, 'Units')

        # Extract domain/enumeration values
        domain = self.extract_domain(soup)

        # Determine if continuous or categorical
        is_continuous = self.is_continuous_variable(var_type, soup)

        # Extract statistics for continuous variables
        if is_continuous:
            stats_by_visit = self.extract_statistics(soup)

            if stats_by_visit:
                # Create separate row for each visit
                for visit_name, stats in stats_by_visit.items():
                    self.continuous_vars.append({
                        'study_name': study_id.upper(),
                        'variable_name': var_name,
                        'variable_label': var_label,
                        'folder': folder,
                        'description': description,
                        'visit': visit_name,
                        'domain': domain,
                        'type': var_type,
                        'total_subjects': stats.get('total_subjects', ''),
                        'units': units,
                        'n': stats.get('n', ''),
                        'mean': stats.get('mean', ''),
                        'stddev': stats.get('stddev', ''),
                        'median': stats.get('median', ''),
                        'min': stats.get('min', ''),
                        'max': stats.get('max', ''),
                        'unknown': stats.get('unknown', '')
                    })
            else:
                # No visit-specific data, create single row
                self.continuous_vars.append({
                    'study_name': study_id.upper(),
                    'variable_name': var_name,
                    'variable_label': var_label,
                    'folder': folder,
                    'description': description,
                    'visit': '',
                    'domain': domain,
                    'type': var_type,
                    'total_subjects': '',
                    'units': units,
                    'n': '',
                    'mean': '',
                    'stddev': '',
                    'median': '',
                    'min': '',
                    'max': '',
                    'unknown': ''
                })
        else:
            # Categorical variable
            visits = self.extract_categorical_visits(soup)

            if visits:
                # Create separate row for each visit
                for visit_name in visits:
                    self.categorical_vars.append({
                        'study_name': study_id.upper(),
                        'variable_name': var_name,
                        'variable_label': var_label,
                        'folder': folder,
                        'description': description,
                        'visit': visit_name,
                        'domain': domain,
                        'type': var_type
                    })
            else:
                # No visit-specific data, create single row
                self.categorical_vars.append({
                    'study_name': study_id.upper(),
                    'variable_name': var_name,
                    'variable_label': var_label,
                    'folder': folder,
                    'description': description,
                    'visit': '',
                    'domain': domain,
                    'type': var_type
                })

    def extract_text(self, soup: BeautifulSoup, label: str) -> str:
        """Extract text value for a given label"""
        # Try multiple strategies to find the text

        # Strategy 1: Look for dt/dd pairs
        for dt in soup.find_all('dt'):
            if label.lower() in dt.get_text().lower():
                dd = dt.find_next_sibling('dd')
                if dd:
                    return dd.get_text(strip=True)

        # Strategy 2: Look for strong/b tags followed by text
        for tag in soup.find_all(['strong', 'b']):
            if label.lower() in tag.get_text().lower():
                parent = tag.parent
                text = parent.get_text(strip=True)
                # Remove the label part
                text = re.sub(rf'{re.escape(label)}:?\s*', '', text, flags=re.IGNORECASE)
                return text

        # Strategy 3: Look for divs with specific classes
        for div in soup.find_all('div', class_=re.compile('variable-')):
            if label.lower() in div.get_text().lower():
                return div.get_text(strip=True)

        return ''

    def extract_domain(self, soup: BeautifulSoup) -> str:
        """Extract domain/enumeration values in pipe-delimited format"""
        domain_values = []

        # Look for enumeration tables or lists
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    code = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    if code and value:
                        domain_values.append(f"{code}:{value}")

        # Look for lists
        for ul in soup.find_all(['ul', 'ol']):
            for li in ul.find_all('li'):
                text = li.get_text(strip=True)
                # Try to parse "code: value" format
                match = re.match(r'^(\d+|[A-Za-z]+):\s*(.+)$', text)
                if match:
                    domain_values.append(f"{match.group(1)}:{match.group(2)}")

        return '|'.join(domain_values) if domain_values else ''

    def is_continuous_variable(self, var_type: str, soup: BeautifulSoup) -> bool:
        """Determine if variable is continuous based on type and presence of statistics"""
        if not var_type:
            # Check for presence of mean/stddev in the page
            text = soup.get_text().lower()
            if 'mean' in text and ('stddev' in text or 'std dev' in text or 'standard deviation' in text):
                return True
            return False

        var_type_lower = var_type.lower()

        # Continuous types
        if any(t in var_type_lower for t in ['numeric', 'integer', 'float', 'continuous']):
            return True

        # Categorical types
        if any(t in var_type_lower for t in ['choice', 'categorical', 'enumeration', 'binary']):
            return False

        # Default: check for statistics
        text = soup.get_text().lower()
        return 'mean' in text and 'stddev' in text

    def extract_statistics(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """Extract statistics organized by visit"""
        stats_by_visit = {}

        # Look for tables with statistics
        for table in soup.find_all('table'):
            headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]

            # Check if this is a statistics table
            if not any(h in headers for h in ['n', 'mean', 'median']):
                continue

            # Extract column indices
            col_indices = {}
            for i, h in enumerate(headers):
                if 'visit' in h or 'timepoint' in h or 'time point' in h:
                    col_indices['visit'] = i
                elif h == 'n' or h == 'count':
                    col_indices['n'] = i
                elif 'mean' in h:
                    col_indices['mean'] = i
                elif 'std' in h or 'sd' in h:
                    col_indices['stddev'] = i
                elif 'median' in h:
                    col_indices['median'] = i
                elif 'min' in h or 'minimum' in h:
                    col_indices['min'] = i
                elif 'max' in h or 'maximum' in h:
                    col_indices['max'] = i

            # Extract rows
            for row in table.find_all('tr')[1:]:  # Skip header
                cols = row.find_all(['td', 'th'])
                if not cols:
                    continue

                # Determine visit name
                visit_name = ''
                if 'visit' in col_indices:
                    visit_name = cols[col_indices['visit']].get_text(strip=True)
                else:
                    # Try to extract from first column
                    visit_name = cols[0].get_text(strip=True)

                if not visit_name:
                    visit_name = 'baseline'

                # Extract statistics
                stats = {}
                for key, idx in col_indices.items():
                    if key != 'visit' and idx < len(cols):
                        value = cols[idx].get_text(strip=True)
                        # Parse values like "45.2 ± 3.1"
                        if '±' in value:
                            parts = value.split('±')
                            if key == 'mean':
                                stats['mean'] = parts[0].strip()
                                stats['stddev'] = parts[1].strip()
                        else:
                            stats[key] = value

                if stats:
                    stats_by_visit[visit_name] = stats

        # Alternative: Look for pipe-delimited values in text
        if not stats_by_visit:
            text = soup.get_text()

            # Look for patterns like "n: 49|43|40" or "mean: 38.9|36.3|36.2"
            n_match = re.search(r'n:\s*(\d+(?:\|\d+)+)', text, re.IGNORECASE)
            mean_match = re.search(r'mean:\s*([\d.]+(?:\|[\d.]+)+)', text, re.IGNORECASE)

            if n_match and mean_match:
                n_values = n_match.group(1).split('|')
                mean_values = mean_match.group(1).split('|')

                # Try to find visit names
                visit_names = self.extract_visit_names(soup, len(n_values))

                for i, (n, mean) in enumerate(zip(n_values, mean_values)):
                    visit_name = visit_names[i] if i < len(visit_names) else f"visit_{i+1}"
                    stats_by_visit[visit_name] = {
                        'n': n,
                        'mean': mean
                    }

        return stats_by_visit

    def extract_visit_names(self, soup: BeautifulSoup, count: int) -> List[str]:
        """Try to extract visit names from context"""
        text = soup.get_text()

        # Common patterns
        visit_patterns = [
            r'baseline',
            r'(\d+)-?month(?:\s+(?:followup|follow-up))?',
            r'(\d+)-?year(?:\s+(?:followup|follow-up))?',
            r'screening',
            r'visit\s+(\d+)',
            r'timepoint\s+(\d+)',
            r'exam\s+(\d+)'
        ]

        visits = []
        for pattern in visit_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                visits.append(match.group(0).lower())
                if len(visits) >= count:
                    return visits[:count]

        # Default names
        return [f"visit_{i+1}" for i in range(count)]

    def extract_categorical_visits(self, soup: BeautifulSoup) -> List[str]:
        """Extract visit names for categorical variables"""
        visits = []

        # Look for tables with visit columns
        for table in soup.find_all('table'):
            headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]

            if 'visit' in headers or 'timepoint' in headers:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all(['td', 'th'])
                    if cols:
                        visit = cols[0].get_text(strip=True)
                        if visit and visit.lower() not in visits:
                            visits.append(visit.lower())

        return visits

    def save_results(self):
        """Save extracted data to TSV files"""
        # Save continuous variables
        continuous_file = '/Users/athessen/sleep-cde-schema/continuous_variables.tsv'
        with open(continuous_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, delimiter='\t', fieldnames=[
                'study_name', 'variable_name', 'variable_label', 'folder',
                'description', 'visit', 'domain', 'type', 'total_subjects',
                'units', 'n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown'
            ])
            writer.writeheader()
            writer.writerows(self.continuous_vars)

        print(f"\nSaved {len(self.continuous_vars)} continuous variable rows to {continuous_file}")

        # Save categorical variables
        categorical_file = '/Users/athessen/sleep-cde-schema/categorical_variables.tsv'
        with open(categorical_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, delimiter='\t', fieldnames=[
                'study_name', 'variable_name', 'variable_label', 'folder',
                'description', 'visit', 'domain', 'type'
            ])
            writer.writeheader()
            writer.writerows(self.categorical_vars)

        print(f"Saved {len(self.categorical_vars)} categorical variable rows to {categorical_file}")

        # Print summary
        print(f"\n{'='*80}")
        print("EXTRACTION SUMMARY")
        print(f"{'='*80}")
        print(f"Total continuous variable rows: {len(self.continuous_vars)}")
        print(f"Total categorical variable rows: {len(self.categorical_vars)}")

        # Count by study
        continuous_by_study = {}
        categorical_by_study = {}

        for var in self.continuous_vars:
            study = var['study_name']
            continuous_by_study[study] = continuous_by_study.get(study, 0) + 1

        for var in self.categorical_vars:
            study = var['study_name']
            categorical_by_study[study] = categorical_by_study.get(study, 0) + 1

        print(f"\nVariables per study:")
        all_studies = sorted(set(list(continuous_by_study.keys()) + list(categorical_by_study.keys())))
        for study in all_studies:
            cont = continuous_by_study.get(study, 0)
            cat = categorical_by_study.get(study, 0)
            print(f"  {study}: {cont} continuous + {cat} categorical = {cont + cat} total")

def main():
    extractor = VariableExtractor()

    try:
        extractor.extract_all_studies()
    finally:
        extractor.save_results()

if __name__ == '__main__':
    main()
