#!/usr/bin/env python3
"""
Comprehensive NSRR Variable Metadata Extraction Script

This script visits individual variable pages on sleepdata.org to extract detailed
metadata for all continuous and categorical variables from 31 NSRR sleep studies.

Features:
- Extracts complete metadata from individual variable pages
- Handles multi-visit data (expands into separate rows)
- Rate limiting to avoid server overload
- Comprehensive error handling and logging
- Progress tracking with status updates
"""

import csv
import time
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
from urllib.parse import quote

# Configuration
RATE_LIMIT_DELAY = 1.5  # seconds between requests
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# File paths
CONTINUOUS_INPUT = '/Users/athessen/sleep-cde-schema/continuous_variables.tsv'
CATEGORICAL_INPUT = '/Users/athessen/sleep-cde-schema/categorical_variables.tsv'
CONTINUOUS_OUTPUT = '/Users/athessen/sleep-cde-schema/continuous_variables_updated.tsv'
CATEGORICAL_OUTPUT = '/Users/athessen/sleep-cde-schema/categorical_variables_updated.tsv'
LOG_FILE = '/Users/athessen/sleep-cde-schema/extraction_log.txt'
ERROR_LOG = '/Users/athessen/sleep-cde-schema/extraction_errors.txt'

class Logger:
    """Simple logger for console and file output"""
    def __init__(self, log_file, error_file):
        self.log_file = log_file
        self.error_file = error_file
        self.start_time = datetime.now()

        # Clear log files
        with open(self.log_file, 'w') as f:
            f.write(f"Variable Metadata Extraction Log\n")
            f.write(f"Started: {self.start_time}\n")
            f.write("=" * 80 + "\n\n")

        with open(self.error_file, 'w') as f:
            f.write(f"Error Log\n")
            f.write(f"Started: {self.start_time}\n")
            f.write("=" * 80 + "\n\n")

    def log(self, message, level="INFO"):
        """Log message to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")

    def error(self, message, exception=None):
        """Log error to console and error file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_msg = f"[{timestamp}] [ERROR] {message}"
        if exception:
            error_msg += f"\n  Exception: {str(exception)}"
        print(error_msg, file=sys.stderr)
        with open(self.error_file, 'a') as f:
            f.write(error_msg + "\n")

    def summary(self):
        """Print summary statistics"""
        duration = datetime.now() - self.start_time
        msg = f"\n{'='*80}\nExtraction completed in {duration}\n{'='*80}\n"
        print(msg)
        with open(self.log_file, 'a') as f:
            f.write(msg)


class VariablePageParser:
    """Parser for NSRR variable pages"""

    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def fetch_page(self, study: str, variable: str, retry_count=0) -> Optional[BeautifulSoup]:
        """Fetch and parse a variable page with retry logic"""
        # IMPORTANT: URLs are case-sensitive, study names must be lowercase
        url = f"https://sleepdata.org/datasets/{study.lower()}/variables/{variable}"

        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)

            if response.status_code == 404:
                self.logger.error(f"Variable page not found: {url}")
                return None

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')

            # DEBUG: Log page info for BMI variables
            if variable == 'bmi':
                num_tables = len(soup.find_all('table'))
                content_len = len(response.text)
                self.logger.log(f"    [FETCH] {url}: {content_len} bytes, {num_tables} tables", "DEBUG")
                if num_tables == 0:
                    # Save problematic HTML for inspection
                    with open('/tmp/bmi_page_debug.html', 'w') as f:
                        f.write(response.text)
                    self.logger.log(f"    [FETCH] Saved HTML to /tmp/bmi_page_debug.html", "DEBUG")

            return soup

        except Exception as e:
            if retry_count < MAX_RETRIES:
                self.logger.log(f"Retry {retry_count + 1}/{MAX_RETRIES} for {study}/{variable}", "WARN")
                time.sleep(RETRY_DELAY)
                return self.fetch_page(study, variable, retry_count + 1)
            else:
                self.logger.error(f"Failed to fetch {url}", e)
                return None

    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extract full description from page"""
        # Strategy 1: Look for form-group with Label
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div and 'label' in label_div.get_text().lower():
                value_div = form_group.find('div', class_='form-control-plaintext')
                if value_div:
                    text = value_div.get_text(strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    return text

        # Strategy 2: Try different selectors for description
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

        # Strategy 3: Look for description in metadata table
        for row in soup.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                if 'description' in cells[0].get_text().lower():
                    return cells[1].get_text(strip=True)

        return ""

    def extract_type(self, soup: BeautifulSoup) -> str:
        """Extract variable type"""
        # Strategy 1: Look for form-group with Type
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div and 'type' in label_div.get_text().lower():
                value_div = form_group.find('div', class_='form-control-plaintext')
                if value_div:
                    return value_div.get_text(strip=True)

        # Strategy 2: Look for type in metadata rows
        for row in soup.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                header = cells[0].get_text().strip().lower()
                if header in ['type', 'variable type', 'data type']:
                    return cells[1].get_text(strip=True)

        return ""

    def extract_units(self, soup: BeautifulSoup) -> str:
        """Extract units for continuous variables"""
        # Strategy 1: Look for form-group with Units
        for form_group in soup.find_all('div', class_='form-group'):
            label_div = form_group.find('div', class_='col-form-label')
            if label_div and 'units' in label_div.get_text().lower():
                value_div = form_group.find('div', class_='form-control-plaintext')
                if value_div:
                    units = value_div.get_text(strip=True)
                    units = re.sub(r'\s+', ' ', units)
                    return units

        # Strategy 2: Look for units in metadata rows
        for row in soup.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                header = cells[0].get_text().strip().lower()
                if header in ['units', 'unit', 'measurement unit']:
                    units = cells[1].get_text(strip=True)
                    units = re.sub(r'\s+', ' ', units)
                    return units

        # Strategy 3: Try to find units in description or label
        desc = self.extract_description(soup)
        unit_patterns = [
            r'\(([^)]*(?:kg|cm|m²|mmHg|events?/h|%|min|sec|years?|days?|hours?)[^)]*)\)',
            r'in\s+([^.\n]+(?:kg|cm|m²|mmHg|events?/h|%|min|sec|years?|days?|hours?))',
        ]

        for pattern in unit_patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def extract_domain(self, soup: BeautifulSoup) -> str:
        """Extract domain/choices for categorical variables in pipe-delimited format"""
        # Strategy 0: Look for bullet list with code:value format (most common for NSRR)
        # Find all list items
        for ul in soup.find_all(['ul', 'ol']):
            choices = []
            for li in ul.find_all('li', recursive=False):  # Only direct children
                text = li.get_text(strip=True)
                # Try to parse "code: label" or "code - label" format
                # Match patterns like "1: white", "1 - white", "1 white"
                match = re.match(r'^([0-9a-zA-Z]+)\s*[:\-]\s*(.+)$', text)
                if match:
                    code = match.group(1).strip()
                    label = match.group(2).strip()
                    label = re.sub(r'\s+', ' ', label)
                    choices.append(f"{code}:{label}")

            # Only return if we found at least 2 choices
            if len(choices) >= 2:
                return '|'.join(choices)

        # Strategy 1: Look for tables with code/value columns
        for table in soup.find_all('table'):
            # Check table headers
            header_row = table.find('tr')
            if not header_row:
                continue

            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

            # Look for code/value columns
            code_col = None
            label_col = None

            for i, header in enumerate(headers):
                if header in ['code', 'value', 'id', 'number', 'key']:
                    code_col = i
                elif header in ['label', 'description', 'meaning', 'text', 'name', 'category']:
                    label_col = i

            # If we found both columns, extract data
            if code_col is not None and label_col is not None:
                choices = []
                for row in table.find_all('tr')[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > max(code_col, label_col):
                        code = cells[code_col].get_text(strip=True)
                        label = cells[label_col].get_text(strip=True)

                        # Skip empty or header-like rows
                        if not code or not label or code.lower() in headers:
                            continue

                        # Clean label
                        label = re.sub(r'\s+', ' ', label)
                        choices.append(f"{code}:{label}")

                if choices:
                    return '|'.join(choices)

        # Strategy 2: Look for sections with "Choices" or "Domain" headers
        domain_headers = ['choices', 'domain', 'values', 'categories', 'codes', 'levels']

        for header_text in domain_headers:
            for header in soup.find_all(['h2', 'h3', 'h4', 'strong', 'b']):
                if header_text in header.get_text().lower():
                    # Look for table after header
                    table = header.find_next('table')
                    if table:
                        choices = []
                        for row in table.find_all('tr')[1:]:  # Skip header row
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                code = cells[0].get_text(strip=True)
                                label = cells[1].get_text(strip=True)

                                if not code or not label:
                                    continue

                                # Clean label
                                label = re.sub(r'\s+', ' ', label)
                                choices.append(f"{code}:{label}")

                        if choices:
                            return '|'.join(choices)

                    # Look for list after header
                    ul = header.find_next('ul')
                    if ul:
                        choices = []
                        for li in ul.find_all('li'):
                            text = li.get_text(strip=True)
                            # Try to parse "code: label" or "code - label" format
                            match = re.match(r'^(\d+)\s*[:\-]\s*(.+)$', text)
                            if match:
                                code = match.group(1)
                                label = match.group(2)
                                label = re.sub(r'\s+', ' ', label)
                                choices.append(f"{code}:{label}")

                        if choices:
                            return '|'.join(choices)

        # Strategy 3: Look for definition lists
        for dl in soup.find_all('dl'):
            choices = []
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            if len(dts) == len(dds) and len(dts) > 0:
                for dt, dd in zip(dts, dds):
                    code = dt.get_text(strip=True)
                    label = dd.get_text(strip=True)

                    if not code or not label:
                        continue

                    label = re.sub(r'\s+', ' ', label)
                    choices.append(f"{code}:{label}")

                if choices:
                    return '|'.join(choices)

        return ""

    def extract_statistics(self, soup: BeautifulSoup, debug=False) -> List[Dict]:
        """
        Extract statistics for continuous variables.
        Returns list of dicts, one per visit if multi-visit data exists.
        """
        if debug:
            self.logger.log(f"    [TRACE] extract_statistics called with debug={debug}, soup type={type(soup)}", "DEBUG")

        stats_list = []

        # Look for statistics table
        all_tables = soup.find_all('table')
        if debug:
            self.logger.log(f"    [TRACE] Found {len(all_tables)} total tables in soup", "DEBUG")

        table_count = 0
        for table in all_tables:
            table_count += 1
            # Get all header cells
            header_row = table.find('tr')
            if not header_row:
                continue

            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

            # Check if this is a statistics table (has statistics columns)
            stats_headers = ['n', 'mean', 'median', 'min', 'max', 'std', 'stddev']
            if not any(h in headers for h in stats_headers):
                if debug:
                    self.logger.log(f"    Table {table_count}: No stats headers, skipping. Headers: {headers[:3]}", "DEBUG")
                continue

            if debug:
                self.logger.log(f"    Table {table_count}: Stats table found with headers: {headers}", "DEBUG")

            # Find column indices for each statistic
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

            # Extract data rows (each row is a visit or category)
            for row in table.find_all('tr')[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                if len(cells) <= 1:
                    continue

                # First cell is typically the visit/category name
                visit_name = cells[0].get_text(strip=True)

                # Skip rows that are subtotals or don't look like visits
                if visit_name.lower() in ['total', 'all', 'overall', '']:
                    if debug:
                        self.logger.log(f"      Row '{visit_name}': Skipped (total/subtotal)", "DEBUG")
                    continue

                # Only include rows that look like visits (not demographics breakdowns)
                # Visit keywords: baseline, followup, follow-up, month, year, visit, screening
                visit_keywords = ['baseline', 'followup', 'follow-up', 'month', 'year', 'visit',
                                  'screening', 'week', 'day', 'v1', 'v2', 'v3', 'v4', 'v5',
                                  'pre', 'post', 'initial', 'final', 'cycle', 'phase']

                # Skip demographic categories (treatment arms, age groups, gender, race)
                skip_keywords = ['male', 'female', 'treatment', 'arm', 'cpap', 'lgb',
                                'white', 'black', 'asian', 'hispanic', 'latino',
                                'race', 'ethnicity', 'gender', 'sex']

                visit_lower = visit_name.lower()

                # Skip if it contains skip keywords
                if any(skip in visit_lower for skip in skip_keywords):
                    if debug:
                        self.logger.log(f"      Row '{visit_name}': Skipped (demographic keyword)", "DEBUG")
                    continue

                # Skip age ranges (e.g., "27.0 to 45.0 years", "20-30 years")
                if re.search(r'\d+\.?\d*\s*(?:to|-)\s*\d+\.?\d*\s*(?:year|age)', visit_lower):
                    if debug:
                        self.logger.log(f"      Row '{visit_name}': Skipped (age range)", "DEBUG")
                    continue

                # Include if it contains visit keywords, or if this is the first table (likely main stats)
                if not any(keyword in visit_lower for keyword in visit_keywords):
                    # If no visit keywords found, this might be a demographic breakdown - skip
                    if debug:
                        self.logger.log(f"      Row '{visit_name}': Skipped (no visit keywords)", "DEBUG")
                    continue

                if debug:
                    self.logger.log(f"      Row '{visit_name}': ACCEPTED as visit row", "DEBUG")

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
                        # Clean up value - remove ± symbol and other non-numeric chars except . and -
                        value = value.replace('±', '').strip()
                        value = re.sub(r'[^\d.\-]', '', value)
                        visit_stats[stat_name] = value

                stats_list.append(visit_stats)

        # If no table found, try to extract from text
        if not stats_list:
            # Look for pipe-delimited values
            text = soup.get_text()
            patterns = {
                'n': r'N[:=]\s*(\d+(?:\|\d+)*)',
                'mean': r'[Mm]ean[:=]\s*([\d.]+(?:\|[\d.]+)*)',
                'stddev': r'(?:[Ss]td|SD)[:=]\s*([\d.]+(?:\|[\d.]+)*)',
                'median': r'[Mm]edian[:=]\s*([\d.]+(?:\|[\d.]+)*)',
            }

            pipe_data = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                if match:
                    pipe_data[key] = match.group(1).split('|')

            if pipe_data:
                num_visits = max(len(v) for v in pipe_data.values())
                for i in range(num_visits):
                    visit_stats = {
                        'visit': '',
                        'n': pipe_data.get('n', [''])[i] if i < len(pipe_data.get('n', [])) else '',
                        'mean': pipe_data.get('mean', [''])[i] if i < len(pipe_data.get('mean', [])) else '',
                        'stddev': pipe_data.get('stddev', [''])[i] if i < len(pipe_data.get('stddev', [])) else '',
                        'median': pipe_data.get('median', [''])[i] if i < len(pipe_data.get('median', [])) else '',
                        'min': '',
                        'max': '',
                        'unknown': '',
                    }
                    stats_list.append(visit_stats)

        return stats_list if stats_list else [{}]  # Return at least one empty dict

    def _extract_stat(self, stat_data: Dict, keys, index: int) -> str:
        """Helper to extract a statistic value"""
        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            if key in stat_data and index < len(stat_data[key]):
                value = stat_data[key][index]
                # Clean up value
                value = re.sub(r'[^\d.\-]', '', value)  # Keep only numbers, dots, minus
                return value

        return ""

    def parse_continuous_variable(self, study: str, variable: str) -> List[Dict]:
        """Parse a continuous variable page and return list of rows (one per visit if applicable)"""
        soup = self.fetch_page(study, variable)
        if not soup:
            return []

        # Extract common fields
        description = self.extract_description(soup)
        var_type = self.extract_type(soup)
        units = self.extract_units(soup)

        # Extract statistics (may be multiple visits)
        debug_var = variable == 'bmi'  # Debug for BMI variables
        if debug_var:
            self.logger.log(f"  [DEBUG] Extracting statistics for {study}/{variable}", "DEBUG")
        stats_list = self.extract_statistics(soup, debug=debug_var)

        # Build result rows
        rows = []
        for stats in stats_list:
            row = {
                'description': description,
                'type': var_type,
                'units': units,
                'visit': stats.get('visit', ''),
                'n': stats.get('n', ''),
                'mean': stats.get('mean', ''),
                'stddev': stats.get('stddev', ''),
                'median': stats.get('median', ''),
                'min': stats.get('min', ''),
                'max': stats.get('max', ''),
                'unknown': stats.get('unknown', ''),
            }
            rows.append(row)

        return rows if rows else [{'description': description, 'type': var_type, 'units': units}]

    def parse_categorical_variable(self, study: str, variable: str) -> Dict:
        """Parse a categorical variable page and return metadata"""
        soup = self.fetch_page(study, variable)
        if not soup:
            return {}

        description = self.extract_description(soup)
        var_type = self.extract_type(soup)
        domain = self.extract_domain(soup)

        return {
            'description': description,
            'type': var_type,
            'domain': domain,
        }


def process_continuous_variables(logger):
    """Process all continuous variables"""
    logger.log("Starting continuous variables extraction")
    logger.log(f"Reading from: {CONTINUOUS_INPUT}")

    parser = VariablePageParser(logger)

    # Read input
    with open(CONTINUOUS_INPUT, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        input_rows = list(reader)
        fieldnames = reader.fieldnames

    logger.log(f"Found {len(input_rows)} continuous variables to process")

    # Process each variable
    output_rows = []
    success_count = 0
    error_count = 0
    expanded_count = 0

    for i, row in enumerate(input_rows, 1):
        study = row['study_name']
        variable = row['variable_name']

        logger.log(f"[{i}/{len(input_rows)}] Processing {study}/{variable}")

        try:
            # Parse variable page
            parsed_rows = parser.parse_continuous_variable(study, variable)

            # DEBUG: Log what we got back
            if i <= 10 or variable == 'bmi':  # Log first 10 and any BMI variables
                logger.log(f"  DEBUG: Received {len(parsed_rows)} rows from parser", "DEBUG")
                if len(parsed_rows) > 0:
                    logger.log(f"  DEBUG: First row keys: {list(parsed_rows[0].keys())}", "DEBUG")
                    logger.log(f"  DEBUG: First row sample: visit={parsed_rows[0].get('visit')}, n={parsed_rows[0].get('n')}, mean={parsed_rows[0].get('mean')}", "DEBUG")

            if parsed_rows:
                # Update each row with parsed data
                for parsed in parsed_rows:
                    new_row = row.copy()

                    # Update with parsed data
                    if parsed.get('description'):
                        new_row['description'] = parsed['description']
                    if parsed.get('type'):
                        new_row['type'] = parsed['type']
                    if parsed.get('units'):
                        new_row['units'] = parsed['units']
                    if parsed.get('visit'):
                        new_row['visit'] = parsed['visit']
                    if parsed.get('n'):
                        new_row['n'] = parsed['n']
                    if parsed.get('mean'):
                        new_row['mean'] = parsed['mean']
                    if parsed.get('stddev'):
                        new_row['stddev'] = parsed['stddev']
                    if parsed.get('median'):
                        new_row['median'] = parsed['median']
                    if parsed.get('min'):
                        new_row['min'] = parsed['min']
                    if parsed.get('max'):
                        new_row['max'] = parsed['max']
                    if parsed.get('unknown'):
                        new_row['unknown'] = parsed['unknown']

                    output_rows.append(new_row)

                success_count += 1
                if len(parsed_rows) > 1:
                    expanded_count += 1
                    logger.log(f"  → Expanded into {len(parsed_rows)} visit rows")
            else:
                # Keep original row if parsing failed
                output_rows.append(row)
                error_count += 1

        except Exception as e:
            logger.error(f"Error processing {study}/{variable}", e)
            output_rows.append(row)
            error_count += 1

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

        # Progress update every 50 variables
        if i % 50 == 0:
            logger.log(f"Progress: {i}/{len(input_rows)} ({i*100//len(input_rows)}%) - Success: {success_count}, Errors: {error_count}, Expanded: {expanded_count}")

    # Write output
    logger.log(f"Writing results to: {CONTINUOUS_OUTPUT}")
    with open(CONTINUOUS_OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(output_rows)

    logger.log(f"Continuous variables complete: {len(output_rows)} rows written ({len(input_rows)} → {len(output_rows)})")
    logger.log(f"Success: {success_count}, Errors: {error_count}, Expanded: {expanded_count}")

    return success_count, error_count


def process_categorical_variables(logger):
    """Process all categorical variables"""
    logger.log("Starting categorical variables extraction")
    logger.log(f"Reading from: {CATEGORICAL_INPUT}")

    parser = VariablePageParser(logger)

    # Read input
    with open(CATEGORICAL_INPUT, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        input_rows = list(reader)
        fieldnames = reader.fieldnames

    logger.log(f"Found {len(input_rows)} categorical variables to process")

    # Process each variable
    output_rows = []
    success_count = 0
    error_count = 0

    for i, row in enumerate(input_rows, 1):
        study = row['study_name']
        variable = row['variable_name']

        logger.log(f"[{i}/{len(input_rows)}] Processing {study}/{variable}")

        try:
            # Parse variable page
            parsed = parser.parse_categorical_variable(study, variable)

            if parsed:
                # Update row with parsed data
                if parsed.get('description'):
                    row['description'] = parsed['description']
                if parsed.get('type'):
                    row['type'] = parsed['type']
                if parsed.get('domain'):
                    row['domain'] = parsed['domain']

                success_count += 1
            else:
                error_count += 1

            output_rows.append(row)

        except Exception as e:
            logger.error(f"Error processing {study}/{variable}", e)
            output_rows.append(row)
            error_count += 1

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

        # Progress update every 50 variables
        if i % 50 == 0:
            logger.log(f"Progress: {i}/{len(input_rows)} ({i*100//len(input_rows)}%) - Success: {success_count}, Errors: {error_count}")

    # Write output
    logger.log(f"Writing results to: {CATEGORICAL_OUTPUT}")
    with open(CATEGORICAL_OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(output_rows)

    logger.log(f"Categorical variables complete: {len(output_rows)} rows written")
    logger.log(f"Success: {success_count}, Errors: {error_count}")

    return success_count, error_count


def main():
    """Main execution function"""
    logger = Logger(LOG_FILE, ERROR_LOG)

    logger.log("=" * 80)
    logger.log("NSRR Variable Metadata Extraction")
    logger.log("=" * 80)
    logger.log(f"Rate limit: {RATE_LIMIT_DELAY}s between requests")
    logger.log(f"Timeout: {REQUEST_TIMEOUT}s per request")
    logger.log(f"Max retries: {MAX_RETRIES}")
    logger.log("")

    # Estimate time
    total_vars = 1920 + 586  # 2506 variables
    estimated_time = (total_vars * RATE_LIMIT_DELAY) / 3600  # hours
    logger.log(f"Estimated time: ~{estimated_time:.1f} hours for {total_vars} variables")
    logger.log("")

    try:
        # Process continuous variables
        cont_success, cont_errors = process_continuous_variables(logger)
        logger.log("")

        # Process categorical variables
        cat_success, cat_errors = process_categorical_variables(logger)
        logger.log("")

        # Summary
        logger.log("=" * 80)
        logger.log("EXTRACTION COMPLETE")
        logger.log("=" * 80)
        logger.log(f"Continuous: {cont_success} success, {cont_errors} errors")
        logger.log(f"Categorical: {cat_success} success, {cat_errors} errors")
        logger.log(f"Total: {cont_success + cat_success} success, {cont_errors + cat_errors} errors")
        logger.log(f"Log file: {LOG_FILE}")
        logger.log(f"Error log: {ERROR_LOG}")
        logger.summary()

    except KeyboardInterrupt:
        logger.log("\n\nProcess interrupted by user", "WARN")
        logger.log("Partial results may have been saved")
        sys.exit(1)
    except Exception as e:
        logger.error("Fatal error in main execution", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
