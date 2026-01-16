#!/usr/bin/env python3
"""
Debug script to test HTML parsing on sample variable pages
"""

import requests
from bs4 import BeautifulSoup
import re

def fetch_page(study, variable):
    """Fetch a variable page"""
    url = f"https://sleepdata.org/datasets/{study}/variables/{variable}"
    print(f"\n{'='*80}")
    print(f"Fetching: {url}")
    print('='*80)

    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        print(f"ERROR: HTTP {response.status_code}")
        return None

    return BeautifulSoup(response.text, 'html.parser')

def analyze_statistics_tables(soup):
    """Analyze all tables on the page for statistics"""
    tables = soup.find_all('table')
    print(f"\nFound {len(tables)} tables on the page")

    for idx, table in enumerate(tables, 1):
        print(f"\n--- Table {idx} ---")

        # Check table classes
        classes = table.get('class', [])
        print(f"Classes: {classes}")

        # Get header row
        header_row = table.find('tr')
        if not header_row:
            print("  No header row found")
            continue

        # Get headers
        header_cells = header_row.find_all(['th', 'td'])
        headers = [cell.get_text(strip=True) for cell in header_cells]
        print(f"Headers ({len(headers)}): {headers}")

        # Check which headers match statistics keywords
        headers_lower = [h.lower() for h in headers]
        stats_keywords = ['n', 'mean', 'median', 'min', 'max', 'std', 'stddev']
        matching_stats = [h for h in headers_lower if any(kw in h for kw in stats_keywords)]
        print(f"Statistics headers found: {matching_stats}")

        # Get data rows
        data_rows = table.find_all('tr')[1:]  # Skip header
        print(f"Data rows: {len(data_rows)}")

        # Show first 3 data rows
        for row_idx, row in enumerate(data_rows[:3], 1):
            cells = row.find_all(['td', 'th'])
            cell_values = [cell.get_text(strip=True) for cell in cells]
            print(f"  Row {row_idx} ({len(cell_values)} cells): {cell_values}")

def test_extract_statistics(soup):
    """Test the extract_statistics method from the script"""
    print(f"\n{'='*80}")
    print("TESTING EXTRACT_STATISTICS METHOD")
    print('='*80)

    stats_list = []

    # Look for statistics table
    for table in soup.find_all('table'):
        # Get all header cells
        header_row = table.find('tr')
        if not header_row:
            continue

        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
        print(f"\nChecking table with headers: {headers}")

        # Check if this is a statistics table (has statistics columns)
        stats_headers = ['n', 'mean', 'median', 'min', 'max', 'std', 'stddev']
        matching = [h for h in headers if h in stats_headers]
        print(f"  Matching stats headers: {matching}")

        if not any(h in headers for h in stats_headers):
            print("  ❌ SKIPPED - No statistics headers found")
            continue

        print("  ✓ This looks like a statistics table!")

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

        print(f"  Column indices: {col_indices}")

        # Extract data rows
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) <= 1:
                continue

            # First cell is typically the visit/category name
            visit_name = cells[0].get_text(strip=True)

            print(f"\n  Processing row: '{visit_name}'")

            # Skip rows that are subtotals
            if visit_name.lower() in ['total', 'all', 'overall', '']:
                print(f"    ❌ SKIPPED - Total/subtotal row")
                continue

            # Check for visit keywords
            visit_keywords = ['baseline', 'followup', 'follow-up', 'month', 'year', 'visit',
                              'screening', 'week', 'day', 'v1', 'v2', 'v3', 'v4', 'v5',
                              'pre', 'post', 'initial', 'final', 'cycle', 'phase']

            skip_keywords = ['male', 'female', 'treatment', 'arm', 'cpap', 'lgb',
                            'white', 'black', 'asian', 'hispanic', 'latino',
                            'race', 'ethnicity', 'gender', 'sex']

            visit_lower = visit_name.lower()

            # Check skip keywords
            if any(skip in visit_lower for skip in skip_keywords):
                print(f"    ❌ SKIPPED - Contains demographic keyword")
                continue

            # Check age range pattern
            if re.search(r'\d+\.?\d*\s*(?:to|-)\s*\d+\.?\d*\s*(?:year|age)', visit_lower):
                print(f"    ❌ SKIPPED - Age range pattern")
                continue

            # Check for visit keywords
            if not any(keyword in visit_lower for keyword in visit_keywords):
                print(f"    ❌ SKIPPED - No visit keywords found")
                continue

            print(f"    ✓ ACCEPTED as visit row")

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
                    # Clean up value
                    value = value.replace('±', '').strip()
                    value = re.sub(r'[^\d.\-]', '', value)
                    visit_stats[stat_name] = value
                    print(f"      {stat_name} = '{value}'")

            stats_list.append(visit_stats)

    print(f"\n{'='*80}")
    print(f"RESULTS: Found {len(stats_list)} visit statistics")
    print('='*80)
    for stats in stats_list:
        print(f"  {stats}")

    return stats_list

def test_extract_units(soup):
    """Test units extraction"""
    print(f"\n{'='*80}")
    print("TESTING UNITS EXTRACTION")
    print('='*80)

    # Strategy 1: Look for form-group with Units
    for form_group in soup.find_all('div', class_='form-group'):
        label_div = form_group.find('div', class_='col-form-label')
        if label_div and 'units' in label_div.get_text().lower():
            value_div = form_group.find('div', class_='form-control-plaintext')
            if value_div:
                units = value_div.get_text(strip=True)
                units = re.sub(r'\s+', ' ', units)
                print(f"Found units in form-group: '{units}'")
                return units

    print("No units found in form-groups")
    return ""

def test_extract_domain(soup):
    """Test domain extraction for categorical variables"""
    print(f"\n{'='*80}")
    print("TESTING DOMAIN EXTRACTION")
    print('='*80)

    # Look for bullet lists
    for ul in soup.find_all(['ul', 'ol']):
        print(f"\nFound list with {len(ul.find_all('li', recursive=False))} items")
        choices = []
        for li in ul.find_all('li', recursive=False):
            text = li.get_text(strip=True)
            print(f"  Item: '{text}'")
            # Try to parse "code: label" or "code - label" format
            match = re.match(r'^([0-9a-zA-Z]+)\s*[:\-]\s*(.+)$', text)
            if match:
                code = match.group(1).strip()
                label = match.group(2).strip()
                label = re.sub(r'\s+', ' ', label)
                choices.append(f"{code}:{label}")
                print(f"    ✓ Parsed as: {code}:{label}")

        if len(choices) >= 2:
            domain = '|'.join(choices)
            print(f"\n✓ Found domain: {domain}")
            return domain

    print("No domain found")
    return ""

# Test on sample variables
test_cases = [
    ('abc', 'bmi'),  # Continuous with multi-visit
    ('abc', 'gender'),  # Categorical
    ('mesa', 'age5c'),  # Another continuous
]

for study, variable in test_cases:
    soup = fetch_page(study, variable)
    if soup:
        analyze_statistics_tables(soup)
        test_extract_statistics(soup)
        test_extract_units(soup)
        test_extract_domain(soup)
        print("\n" + "="*80 + "\n")
