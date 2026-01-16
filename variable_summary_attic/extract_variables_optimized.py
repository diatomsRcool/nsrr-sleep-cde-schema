#!/usr/bin/env python3
"""
Optimized variable extraction - generates commands for parallel processing
"""

import json

STUDIES = [
    'abc', 'answers', 'apoe', 'apples', 'bestair', 'ccshs', 'cfs', 'chat',
    'disecad', 'fdcsr', 'ffcws', 'haassa', 'hchs', 'heartbeat', 'homepap',
    'isaps', 'lofthf', 'mesa', 'mros', 'msp', 'nchsdb', 'nfs', 'numom2b',
    'pats', 'pimecfs', 'sandd', 'shine', 'shhs', 'sof', 'stages', 'wsc'
]

def generate_extraction_commands():
    """Generate wget commands to download variable list pages"""

    print("# Download variable list pages for all studies")
    print("mkdir -p /tmp/sleepdata_vars")
    print()

    for study in STUDIES:
        url = f"https://sleepdata.org/datasets/{study}/variables"
        output = f"/tmp/sleepdata_vars/{study}_variables.html"
        print(f"wget -q -O {output} '{url}' && echo '{study}: done' &")

    print("\nwait")
    print("\necho 'All variable lists downloaded!'")

def generate_study_info():
    """Generate study information JSON"""
    study_info = {study: {"url": f"https://sleepdata.org/datasets/{study}/variables"} for study in STUDIES}

    with open('/Users/athessen/sleep-cde-schema/study_urls.json', 'w') as f:
        json.dump(study_info, f, indent=2)

    print(f"Generated study_urls.json with {len(STUDIES)} studies")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'commands':
        generate_extraction_commands()
    else:
        generate_study_info()
