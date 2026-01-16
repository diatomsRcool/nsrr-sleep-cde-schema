#!/usr/bin/env python3
"""
Compile all extracted variables into TSV files
"""

import json
import csv

# Store all extracted data
all_variables = {}

# ABC Study
all_variables['ABC'] = [
    {"variable_name": "nsrrid", "variable_label": "NSRR subject identifier", "folder": "Administrative", "type": "identifier"},
    {"variable_name": "rand_siteid", "variable_label": "Site identifier", "folder": "Administrative", "type": "categorical"},
    {"variable_name": "rand_treatmentarm", "variable_label": "Randomized treatment arm", "folder": "Administrative", "type": "categorical"},
    {"variable_name": "visitnumber", "variable_label": "Visit number", "folder": "Administrative", "type": "numeric"},
    {"variable_name": "bmi", "variable_label": "Body mass index (BMI)", "folder": "Anthropometry", "type": "numeric"},
    {"variable_name": "height", "variable_label": "Height", "folder": "Anthropometry", "type": "numeric"},
    {"variable_name": "weight", "variable_label": "Weight", "folder": "Anthropometry", "type": "numeric"},
    {"variable_name": "age", "variable_label": "Age of the participant", "folder": "Demographics", "type": "numeric"},
    {"variable_name": "ethnicity", "variable_label": "Ethnicity (Hispanic or Latino) of the participant", "folder": "Demographics", "type": "categorical"},
    {"variable_name": "gender", "variable_label": "Gender of the participant", "folder": "Demographics", "type": "categorical"},
    {"variable_name": "race", "variable_label": "Race of the participant", "folder": "Demographics", "type": "categorical"},
    {"variable_name": "ess_total", "variable_label": "Epworth Sleepiness Scale total score", "folder": "Sleep Questionnaires/Hypersomnia/Epworth Sleepiness Scale", "type": "numeric"},
    {"variable_name": "ahi_ap0uhp3x3u_f1t1", "variable_label": "Apnea-Hypopnea Index with 3% desaturation", "folder": "Sleep Monitoring/Polysomnography", "type": "numeric"},
    {"variable_name": "ahi_ap0uhp3x4u_f1t1", "variable_label": "Apnea-Hypopnea Index with 4% desaturation", "folder": "Sleep Monitoring/Polysomnography", "type": "numeric"},
]

# Function to classify variables
def classify_variable(var):
    """Determine if variable is continuous or categorical"""
    var_type = var.get('type', '').lower()

    # Continuous indicators
    if any(t in var_type for t in ['numeric', 'integer', 'float', 'continuous']):
        return 'continuous'

    # Categorical indicators
    if any(t in var_type for t in ['categorical', 'choice', 'binary', 'enumeration', 'identifier', 'ordinal']):
        return 'categorical'

    # Default based on name patterns
    var_name = var.get('variable_name', '').lower()
    if any(x in var_name for x in ['_id', 'id', 'date', 'time']):
        return 'categorical'

    return 'continuous'  # Default

def generate_tsv_files():
    """Generate TSV files from collected data"""

    continuous_vars = []
    categorical_vars = []

    for study, variables in all_variables.items():
        for var in variables:
            classification = classify_variable(var)

            base_data = {
                'study_name': study,
                'variable_name': var.get('variable_name', ''),
                'variable_label': var.get('variable_label', ''),
                'folder': var.get('folder', ''),
                'description': var.get('description', ''),
                'visit': var.get('visit', ''),
                'domain': var.get('domain', ''),
                'type': var.get('type', '')
            }

            if classification == 'continuous':
                continuous_vars.append({
                    **base_data,
                    'total_subjects': '',
                    'units': var.get('units', ''),
                    'n': '',
                    'mean': '',
                    'stddev': '',
                    'median': '',
                    'min': '',
                    'max': '',
                    'unknown': ''
                })
            else:
                categorical_vars.append(base_data)

    # Write continuous variables
    with open('/Users/athessen/sleep-cde-schema/continuous_variables.tsv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, delimiter='\t', fieldnames=[
            'study_name', 'variable_name', 'variable_label', 'folder',
            'description', 'visit', 'domain', 'type', 'total_subjects',
            'units', 'n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown'
        ])
        writer.writeheader()
        writer.writerows(continuous_vars)

    # Write categorical variables
    with open('/Users/athessen/sleep-cde-schema/categorical_variables.tsv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, delimiter='\t', fieldnames=[
            'study_name', 'variable_name', 'variable_label', 'folder',
            'description', 'visit', 'domain', 'type'
        ])
        writer.writeheader()
        writer.writerows(categorical_vars)

    print(f"Generated {len(continuous_vars)} continuous variables")
    print(f"Generated {len(categorical_vars)} categorical variables")

if __name__ == '__main__':
    generate_tsv_files()
