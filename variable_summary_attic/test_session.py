#!/usr/bin/env python3
"""Test if the session/headers are causing issues"""

import requests
from bs4 import BeautifulSoup
import time

# Test 1: Without session (like my debug script)
print("=" * 80)
print("TEST 1: Direct request (no session)")
print("=" * 80)
response1 = requests.get('https://sleepdata.org/datasets/abc/variables/bmi', timeout=30)
print(f"Status: {response1.status_code}")
print(f"Content length: {len(response1.text)}")
soup1 = BeautifulSoup(response1.text, 'html.parser')
tables1 = soup1.find_all('table')
print(f"Tables found: {len(tables1)}")

time.sleep(2)

# Test 2: With session (like extraction script)
print("\n" + "=" * 80)
print("TEST 2: Session with User-Agent header")
print("=" * 80)
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
})
response2 = session.get('https://sleepdata.org/datasets/abc/variables/bmi', timeout=30)
print(f"Status: {response2.status_code}")
print(f"Content length: {len(response2.text)}")
soup2 = BeautifulSoup(response2.text, 'html.parser')
tables2 = soup2.find_all('table')
print(f"Tables found: {len(tables2)}")

# Check if content is the same
print(f"\nContent identical: {response1.text == response2.text}")

# Check for statistics in first table
if tables2:
    first_table = tables2[0]
    rows = first_table.find_all('tr')
    print(f"\nFirst table has {len(rows)} rows")
    if len(rows) > 0:
        headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
        print(f"Headers: {headers}")
        if len(rows) > 1:
            first_data = [td.get_text(strip=True) for td in rows[1].find_all(['td', 'th'])]
            print(f"First data row: {first_data}")
