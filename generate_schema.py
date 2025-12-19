#!/usr/bin/env python3
"""
Generate LinkML schema from NSRR data dictionary TSV file.
Each row becomes a class with id as the primary identifier.
"""

import csv
import re
from collections import defaultdict
from typing import Dict, List, Set


def safe_class_name(variable_id: str) -> str:
    """Convert variable id to a valid LinkML class name."""
    # Remove any non-alphanumeric characters
    name = re.sub(r'[^\w]', '_', variable_id)
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    # Capitalize first letter
    if name:
        name = name[0].upper() + name[1:]
    return name if name else 'Unknown'


def safe_enum_name(domain: str) -> str:
    """Convert domain name to a valid enum name."""
    name = domain.replace('/', '_').replace(' ', '_')
    name = re.sub(r'[^\w]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    name = ''.join(word.capitalize() for word in name.split('_'))
    if not name.endswith('Enum'):
        name += 'Enum'
    return name


def escape_yaml_string(s: str) -> str:
    """Escape YAML string if needed using single quotes."""
    if not s:
        return "''"

    # Remove all control characters (0x00-0x1F and 0x7F-0x9F)
    cleaned = []
    for char in s:
        code = ord(char)
        if code >= 32 and code < 127:  # Printable ASCII
            cleaned.append(char)
        elif code >= 160:  # Valid Unicode above C1 control range
            cleaned.append(char)
        elif char in ['\t', '\n', '\r']:  # Temporarily keep these for processing
            cleaned.append(char)

    s = ''.join(cleaned)

    # Replace newlines and tabs with spaces
    s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')

    # Normalize multiple spaces to single space
    s = ' '.join(s.split())

    if not s:
        return "''"

    # Use single quotes for YAML strings
    s = s.replace("'", "''")
    return f"'{s}'"


def map_type_to_range(var_type: str, domain: str) -> str:
    """Map NSRR type to LinkML range."""
    if var_type == 'choices':
        return safe_enum_name(domain) if domain else 'string'
    elif var_type == 'numeric':
        return 'float'
    elif var_type == 'integer':
        return 'integer'
    elif var_type == 'identifier':
        return 'string'
    elif var_type == 'string':
        return 'string'
    elif var_type == 'text':
        return 'string'
    elif var_type == 'date':
        return 'date'
    elif var_type == 'datetime':
        return 'datetime'
    elif var_type == 'time':
        return 'time'
    else:
        return 'string'


def normalize_unit(unit: str) -> str:
    """Normalize unit to UCUM-like format."""
    if not unit:
        return None

    ucum_map = {
        'years': 'a',
        'year': 'a',
        'months': 'mo',
        'month': 'mo',
        'weeks': 'wk',
        'week': 'wk',
        'days': 'd',
        'day': 'd',
        'hours': 'h',
        'hour': 'h',
        'minutes': 'min',
        'minute': 'min',
        'seconds': 's',
        'second': 's',
        'milliseconds': 'ms',
        'millisecond': 'ms',
        'centimeters': 'cm',
        'centimeters (cm)': 'cm',
        'meters': 'm',
        'kilograms': 'kg',
        'kilograms (kg)': 'kg',
        'grams': 'g',
        'pounds': '[lb_av]',
        'beats per minute': '/min',
        'beats per minute (bpm)': '/min',
        'breaths per minute': '/min',
        'percent': '%',
        '%': '%',
        'kilograms per meter squared (kg/m2)': 'kg/m2',
        'events per hour': '{events}/h',
        'celsius': 'Cel',
        'celsius (c)': 'Cel',
        'fahrenheit': '[degF]',
    }

    unit_lower = unit.lower()
    if unit_lower in ucum_map:
        return ucum_map[unit_lower]

    return unit


def generate_schema(tsv_file: str, output_file: str):
    """Generate LinkML schema from TSV file."""

    # Read TSV
    with open(tsv_file, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        rows = [row for row in reader if row.get('id') and row.get('id') != 'choices']

    # Collect all unique domains for enumerations
    domains: Set[str] = set()
    for row in rows:
        if row['type'] == 'choices' and row['domain']:
            domains.add(row['domain'])

    # Track class names to handle duplicates
    # First pass: count how many times each class name appears
    class_name_counts: Dict[str, int] = {}
    for row in rows:
        var_id = row['id']
        class_name = safe_class_name(var_id)
        class_name_counts[class_name] = class_name_counts.get(class_name, 0) + 1

    # Track usage during generation
    class_names_seen: Dict[str, int] = {}

    # Start building YAML
    yaml_lines = []

    # Header
    yaml_lines.extend([
        'id: https://w3id.org/nsrr/sleep-cde',
        'name: sleep-cde-schema',
        'title: Sleep Common Data Elements Schema',
        'description: >-',
        '  A LinkML schema for representing sleep study data based on the NSRR data dictionary.',
        '  Each variable from the data dictionary is represented as a class.',
        'license: MIT',
        'default_prefix: sleep',
        'default_range: string',
        '',
        'prefixes:',
        '  sleep: https://w3id.org/nsrr/sleep-cde/',
        '  linkml: https://w3id.org/linkml/',
        '  biolink: https://w3id.org/biolink/vocab/',
        '  schema: http://schema.org/',
        '  NCIT: http://purl.obolibrary.org/obo/NCIT_',
        '',
        'imports:',
        '  - linkml:types',
        '',
    ])

    # Classes - each row becomes a class
    yaml_lines.append('classes:')
    yaml_lines.append('')

    for row in rows:
        var_id = row['id']
        base_class_name = safe_class_name(var_id)

        # Handle duplicate class names
        if class_name_counts[base_class_name] > 1:
            # This is a duplicate, need to add a number
            occurrence = class_names_seen.get(base_class_name, 0) + 1
            class_names_seen[base_class_name] = occurrence
            class_name = f"{base_class_name}_{occurrence}"
        else:
            class_name = base_class_name

        var_type = row['type']
        var_range = map_type_to_range(var_type, row['domain'])

        # Class definition
        yaml_lines.append(f'  {class_name}:')

        # Description
        if row['description']:
            desc = row['description'].strip()
            yaml_lines.append(f'    description: {escape_yaml_string(desc)}')
        elif row['display_name']:
            yaml_lines.append(f'    description: {escape_yaml_string(row["display_name"])}')

        # Slots
        yaml_lines.append('    slots:')
        yaml_lines.append('      - id')
        if row['display_name']:
            yaml_lines.append('      - display_name')
        if row['type']:
            yaml_lines.append('      - type')
        if row['units']:
            yaml_lines.append('      - units')
        if row['domain']:
            yaml_lines.append('      - domain')
        if row['calculation']:
            yaml_lines.append('      - calculation')
        if row['commonly_used'] == 'true':
            yaml_lines.append('      - commonly_used')

        # Slot usage
        yaml_lines.append('    slot_usage:')
        yaml_lines.append('      id:')
        yaml_lines.append('        identifier: true')
        yaml_lines.append('        required: true')
        yaml_lines.append(f'        range: string')

        if row['type']:
            yaml_lines.append('      type:')
            yaml_lines.append(f'        range: {var_range}')

        if row['units']:
            ucum_code = normalize_unit(row['units'])
            yaml_lines.append('      units:')
            if ucum_code:
                yaml_lines.append('        unit:')
                yaml_lines.append(f'          ucum_code: {escape_yaml_string(ucum_code)}')
            else:
                yaml_lines.append(f'        range: string')

        yaml_lines.append('')

    # Slots
    yaml_lines.append('slots:')
    yaml_lines.append('')

    yaml_lines.append('  id:')
    yaml_lines.append('    identifier: true')
    yaml_lines.append('    range: string')
    yaml_lines.append('    description: Variable identifier')
    yaml_lines.append('')

    yaml_lines.append('  display_name:')
    yaml_lines.append('    range: string')
    yaml_lines.append('    description: Display name for the variable')
    yaml_lines.append('')

    yaml_lines.append('  type:')
    yaml_lines.append('    range: string')
    yaml_lines.append('    description: Data type of the variable')
    yaml_lines.append('')

    yaml_lines.append('  units:')
    yaml_lines.append('    range: string')
    yaml_lines.append('    description: Units of measurement')
    yaml_lines.append('')

    yaml_lines.append('  domain:')
    yaml_lines.append('    range: string')
    yaml_lines.append('    description: Domain or enumeration name for categorical variables')
    yaml_lines.append('')

    yaml_lines.append('  calculation:')
    yaml_lines.append('    range: string')
    yaml_lines.append('    description: Formula for calculated variables')
    yaml_lines.append('')

    yaml_lines.append('  commonly_used:')
    yaml_lines.append('    range: boolean')
    yaml_lines.append('    description: Flag indicating if this is a commonly used variable')
    yaml_lines.append('')

    # Enumerations
    yaml_lines.append('enums:')
    yaml_lines.append('')

    for domain in sorted(domains):
        enum_name = safe_enum_name(domain)
        yaml_lines.append(f'  {enum_name}:')
        yaml_lines.append(f'    description: Enumeration for {escape_yaml_string(domain)}')
        yaml_lines.append('    permissible_values:')
        yaml_lines.append('      PLACEHOLDER:')
        yaml_lines.append(f'        description: Placeholder for {escape_yaml_string(domain)} values')
        yaml_lines.append('')

    # Write to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(yaml_lines))

    # Count unique and duplicate classes
    unique_classes = sum(1 for count in class_name_counts.values() if count == 1)
    duplicate_classes = sum(count for count in class_name_counts.values() if count > 1)
    total_classes = unique_classes + duplicate_classes

    print(f"Schema generated successfully!")
    print(f"  Classes (one per variable): {total_classes}")
    print(f"    Unique: {unique_classes}")
    print(f"    Duplicates: {duplicate_classes}")
    print(f"  Common slots: 7")
    print(f"  Enums: {len(domains)}")
    print(f"  Output: {output_file}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        print("Usage: python generate_schema.py <input_tsv> <output_yaml>")
        sys.exit(1)

    generate_schema(sys.argv[1], sys.argv[2])
