#!/usr/bin/env python3
"""
Generate LinkML schema from NSRR data dictionary TSV file.
Uses display names to create class hierarchy with subclasses for variables sharing the same display name prefix.
"""

import csv
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def extract_base_class_name(display_name: str) -> str:
    """Extract the base class name from display name (text before colon or full name)."""
    if not display_name:
        return None

    # Split on colon and take the first part
    parts = display_name.split(':', 1)
    base = parts[0].strip()
    return base


def safe_class_name(name: str) -> str:
    """Convert name to a valid LinkML class name."""
    if not name:
        return 'Unknown'

    # Remove any non-alphanumeric characters except spaces
    name = re.sub(r'[^\w\s]', '', name)
    # Replace spaces with nothing (camel case)
    words = name.split()
    name = ''.join(word.capitalize() for word in words)
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')

    return name if name else 'Unknown'


def safe_slot_name(name: str) -> str:
    """Convert name to a valid LinkML slot name (snake_case)."""
    if not name:
        return 'unknown'

    # Convert to lowercase and replace spaces with underscores
    name = name.lower()
    name = re.sub(r'[^\w\s]', '_', name)
    name = re.sub(r'\s+', '_', name)
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')

    return name if name else 'unknown'


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


def extract_variables_from_calculation(calculation: str) -> Set[str]:
    """Extract variable names from a calculation formula."""
    if not calculation:
        return set()

    # Find all potential variable names (alphanumeric with underscores)
    # Exclude numeric literals
    potential_vars = re.findall(r'\b([a-zA-Z][a-zA-Z0-9_]*)\b', calculation)

    return set(potential_vars)


def generate_schema(tsv_file: str, output_file: str):
    """Generate LinkML schema from TSV file."""

    # Read TSV
    with open(tsv_file, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        rows = [row for row in reader if row.get('id') and row.get('id') != 'choices']

    # Group rows by base class name (extracted from display_name)
    base_class_groups: Dict[str, List[dict]] = defaultdict(list)

    for row in rows:
        display_name = row.get('display_name', '')
        base_name = extract_base_class_name(display_name)
        if base_name:
            base_class_groups[base_name].append(row)
        else:
            # No display name, use id as base
            base_class_groups[row['id']].append(row)

    # Collect all unique domains for enumerations
    domains: Set[str] = set()
    for row in rows:
        if row['type'] == 'choices' and row['domain']:
            domains.add(row['domain'])

    # Track all variables that are used in calculations
    calculation_variables: Set[str] = set()
    for row in rows:
        if row.get('calculation'):
            vars_in_calc = extract_variables_from_calculation(row['calculation'])
            calculation_variables.update(vars_in_calc)

    # Start building YAML
    yaml_lines = []

    # Header
    yaml_lines.extend([
        'id: https://w3id.org/nsrr/sleep-cde',
        'name: sleep-cde-schema',
        'title: Sleep Common Data Elements Schema',
        'description: >-',
        '  A LinkML schema for representing sleep study data based on the NSRR data dictionary.',
        '  Variables are organized into classes by their display name prefix, with subclasses for specific variants.',
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

    # Classes
    yaml_lines.append('classes:')
    yaml_lines.append('')

    # Add base Calculation class
    yaml_lines.extend([
        '  Calculation:',
        '    description: Base class for all calculated variables',
        '    abstract: true',
        '    slots:',
        '      - id',
        '      - formula',
        '',
    ])

    # Process each base class group
    for base_name in sorted(base_class_groups.keys()):
        group = base_class_groups[base_name]
        base_class_name = safe_class_name(base_name)

        # If there's only one variable in the group, create a single class
        if len(group) == 1:
            row = group[0]
            var_id = row['id']
            var_type = row['type']
            var_range = map_type_to_range(var_type, row['domain'])
            has_calculation = bool(row.get('calculation'))

            # Determine parent class
            parent_classes = []
            if has_calculation:
                parent_classes.append('Calculation')

            # Class definition
            yaml_lines.append(f'  {base_class_name}:')

            # Description
            if row['description']:
                desc = row['description'].strip()
                yaml_lines.append(f'    description: {escape_yaml_string(desc)}')
            elif row['display_name']:
                yaml_lines.append(f'    description: {escape_yaml_string(row["display_name"])}')

            # Parent class (is_a)
            if parent_classes:
                yaml_lines.append(f'    is_a: {parent_classes[0]}')

            # ID annotation
            yaml_lines.append(f'    id_prefixes:')
            yaml_lines.append(f'      - {var_id}')

            # Exact mappings from labels
            if row.get('labels'):
                labels = [l.strip() for l in row['labels'].split(';') if l.strip()]
                if labels:
                    yaml_lines.append('    exact_mappings:')
                    for label in labels:
                        yaml_lines.append(f'      - {label}')

            # Slots
            yaml_lines.append('    slots:')
            yaml_lines.append('      - id')

            if row['type']:
                yaml_lines.append('      - value')
            if row['units']:
                yaml_lines.append('      - units')
            if has_calculation:
                yaml_lines.append('      - formula')
                # Add slots for variables used in calculation
                vars_in_calc = extract_variables_from_calculation(row['calculation'])
                for var in sorted(vars_in_calc):
                    slot_name = safe_slot_name(var)
                    if slot_name not in ['id', 'value', 'units', 'formula']:
                        yaml_lines.append(f'      - {slot_name}')

            # Slot usage
            yaml_lines.append('    slot_usage:')
            yaml_lines.append('      id:')
            yaml_lines.append('        identifier: true')
            yaml_lines.append('        required: true')
            yaml_lines.append(f'        pattern: "^{var_id}$"')

            if row['type']:
                yaml_lines.append('      value:')
                yaml_lines.append(f'        range: {var_range}')

            if row['units']:
                ucum_code = normalize_unit(row['units'])
                yaml_lines.append('      units:')
                if ucum_code:
                    yaml_lines.append('        unit:')
                    yaml_lines.append(f'          ucum_code: {escape_yaml_string(ucum_code)}')

            if has_calculation:
                yaml_lines.append('      formula:')
                yaml_lines.append(f'        pattern: {escape_yaml_string(row["calculation"])}')

            yaml_lines.append('')

        else:
            # Multiple variables share the same base name - create parent and subclasses

            # Create abstract parent class
            yaml_lines.append(f'  {base_class_name}:')
            yaml_lines.append(f'    description: {escape_yaml_string(base_name)}')
            yaml_lines.append('    abstract: true')
            yaml_lines.append('    slots:')
            yaml_lines.append('      - id')
            yaml_lines.append('      - value')
            yaml_lines.append('')

            # Create subclass for each variable
            for row in group:
                var_id = row['id']
                subclass_name = safe_class_name(var_id)
                var_type = row['type']
                var_range = map_type_to_range(var_type, row['domain'])
                has_calculation = bool(row.get('calculation'))

                # Subclass definition
                yaml_lines.append(f'  {subclass_name}:')

                # Description
                if row['description']:
                    desc = row['description'].strip()
                    yaml_lines.append(f'    description: {escape_yaml_string(desc)}')
                elif row['display_name']:
                    yaml_lines.append(f'    description: {escape_yaml_string(row["display_name"])}')

                # Parent class
                if has_calculation:
                    yaml_lines.append(f'    is_a: {base_class_name}')
                    yaml_lines.append('    mixins:')
                    yaml_lines.append('      - Calculation')
                else:
                    yaml_lines.append(f'    is_a: {base_class_name}')

                # ID annotation
                yaml_lines.append(f'    id_prefixes:')
                yaml_lines.append(f'      - {var_id}')

                # Exact mappings from labels
                if row.get('labels'):
                    labels = [l.strip() for l in row['labels'].split(';') if l.strip()]
                    if labels:
                        yaml_lines.append('    exact_mappings:')
                        for label in labels:
                            yaml_lines.append(f'      - {label}')

                # Additional slots beyond parent
                additional_slots = []
                if row['units']:
                    additional_slots.append('units')
                if has_calculation:
                    additional_slots.append('formula')
                    # Add slots for variables used in calculation
                    vars_in_calc = extract_variables_from_calculation(row['calculation'])
                    for var in sorted(vars_in_calc):
                        slot_name = safe_slot_name(var)
                        if slot_name not in ['id', 'value', 'units', 'formula']:
                            additional_slots.append(slot_name)

                if additional_slots:
                    yaml_lines.append('    slots:')
                    for slot in additional_slots:
                        yaml_lines.append(f'      - {slot}')

                # Slot usage
                yaml_lines.append('    slot_usage:')
                yaml_lines.append('      id:')
                yaml_lines.append('        identifier: true')
                yaml_lines.append('        required: true')
                yaml_lines.append(f'        pattern: "^{var_id}$"')

                yaml_lines.append('      value:')
                yaml_lines.append(f'        range: {var_range}')

                if row['units']:
                    ucum_code = normalize_unit(row['units'])
                    yaml_lines.append('      units:')
                    if ucum_code:
                        yaml_lines.append('        unit:')
                        yaml_lines.append(f'          ucum_code: {escape_yaml_string(ucum_code)}')

                if has_calculation:
                    yaml_lines.append('      formula:')
                    yaml_lines.append(f'        pattern: {escape_yaml_string(row["calculation"])}')

                yaml_lines.append('')

    # Slots
    yaml_lines.append('slots:')
    yaml_lines.append('')

    yaml_lines.extend([
        '  id:',
        '    identifier: true',
        '    range: string',
        '    description: Variable identifier',
        '',
        '  value:',
        '    range: string',
        '    description: The value of the variable',
        '',
        '  units:',
        '    range: string',
        '    description: Units of measurement',
        '',
        '  formula:',
        '    range: string',
        '    description: Formula for calculated variables',
        '',
    ])

    # Add dynamic slots for calculation variables
    all_calc_vars = set()
    for row in rows:
        if row.get('calculation'):
            vars_in_calc = extract_variables_from_calculation(row['calculation'])
            all_calc_vars.update(vars_in_calc)

    for var in sorted(all_calc_vars):
        slot_name = safe_slot_name(var)
        if slot_name not in ['id', 'value', 'units', 'formula']:
            yaml_lines.append(f'  {slot_name}:')
            yaml_lines.append(f'    description: Variable {var} used in calculation')
            yaml_lines.append('    range: string')
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

    # Statistics
    unique_base_classes = len(base_class_groups)
    total_variables = len(rows)
    classes_with_calculations = sum(1 for row in rows if row.get('calculation'))

    print(f"Schema generated successfully!")
    print(f"  Base classes: {unique_base_classes}")
    print(f"  Total variables: {total_variables}")
    print(f"  Variables with calculations: {classes_with_calculations}")
    print(f"  Enums: {len(domains)}")
    print(f"  Output: {output_file}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        print("Usage: python generate_schema.py <input_tsv> <output_yaml>")
        sys.exit(1)

    generate_schema(sys.argv[1], sys.argv[2])
