#!/usr/bin/env python3
"""
Add CURIE column to variable TSV files using curated mappings.
This fast version uses only known keyword-based mappings without API calls.
"""

import csv
import re
from typing import Optional

# File paths
CONTINUOUS_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'
CATEGORICAL_FILE = '/Users/athessen/sleep-cde-schema/categorical_variables_cde_updated.tsv'

# Comprehensive known OBA mappings (biological attributes)
KNOWN_OBA_MAPPINGS = {
    # Anthropometry (sorted by specificity - longer first)
    'body mass index': 'OBA:VT0001259',
    'standing height': 'OBA:VT0001253',
    'body height': 'OBA:VT0001253',
    'body weight': 'OBA:VT0001259',
    'waist circumference': 'OBA:VT0001256',
    'hip circumference': 'OBA:VT0005416',
    'neck circumference': 'OBA:VT0002230',
    'waist-to-hip': 'OBA:VT0001257',
    'waist to hip': 'OBA:VT0001257',
    'height': 'OBA:VT0001253',
    'weight': 'OBA:VT0001259',

    # Vital signs
    'systolic blood pressure': 'OBA:VT0000183',
    'diastolic blood pressure': 'OBA:VT0000183',
    'blood pressure': 'OBA:VT0000183',
    'heart rate': 'OBA:1001087',
    'pulse rate': 'OBA:1001087',
    'respiratory rate': 'OBA:0000562',
    'body temperature': 'OBA:VT0005089',
    'temperature': 'OBA:VT0005089',

    # Sleep duration
    'total sleep time': 'OBA:1000963',
    'sleep duration': 'OBA:1000963',

    # Demographics
    'age at ': 'OBA:0000052',
    'age of ': 'OBA:0000052',
    'age (': 'OBA:0000052',

    # Lab values - lipids
    'total cholesterol': 'OBA:VT0000180',
    'hdl cholesterol': 'OBA:VT0000184',
    'ldl cholesterol': 'OBA:VT0000185',
    'triglyceride': 'OBA:VT0000181',
    'cholesterol': 'OBA:VT0000180',

    # Lab values - glucose/diabetes
    'fasting glucose': 'OBA:VT0000188',
    'blood glucose': 'OBA:VT0000188',
    'hemoglobin a1c': 'OBA:VT0005453',
    'hba1c': 'OBA:VT0005453',
    'insulin': 'OBA:VT0002644',
    'glucose': 'OBA:VT0000188',

    # Lab values - hematology
    'hemoglobin': 'OBA:VT0003030',
    'hematocrit': 'OBA:VT0001588',
    'white blood cell': 'OBA:VT0000217',
    'red blood cell': 'OBA:VT0000216',
    'platelet count': 'OBA:VT0000218',

    # Lab values - renal/liver
    'creatinine': 'OBA:VT0005328',
    'bun': 'OBA:VT0000190',
    'blood urea nitrogen': 'OBA:VT0000190',
    'albumin': 'OBA:VT0005082',
    'bilirubin': 'OBA:VT0000191',

    # Lab values - other
    'c-reactive protein': 'OBA:VT0000214',
    'crp': 'OBA:VT0000214',
    'uric acid': 'OBA:VT0000189',
    'ferritin': 'OBA:VT0000193',
    'thyroid': 'OBA:VT0000186',
    'tsh': 'OBA:VT0000186',

    # Body composition
    'fat mass': 'OBA:VT0010011',
    'lean mass': 'OBA:VT0010012',
    'body fat': 'OBA:VT0010011',

    # HRV
    'heart rate variability': 'OBA:1001087',
    'sdnn': 'OBA:1001087',
    'rmssd': 'OBA:1001087',

    # Spirometry
    'forced vital capacity': 'OBA:VT0001527',
    'fvc': 'OBA:VT0001527',
    'forced expiratory volume': 'OBA:VT0001528',
    'fev1': 'OBA:VT0001528',
    'fev 1': 'OBA:VT0001528',
}

# Comprehensive known OMOP mappings (clinical concepts)
KNOWN_OMOP_MAPPINGS = {
    # Sleep study indices (specific first)
    'apnea-hypopnea index': 'OMOP:4196413',
    'apnea hypopnea index': 'OMOP:4196413',
    'respiratory disturbance index': 'OMOP:4196413',
    'central apnea index': 'OMOP:4145749',
    'obstructive apnea index': 'OMOP:313459',
    'oxygen desaturation index': 'OMOP:40762499',
    'arousal index': 'OMOP:4214782',
    'periodic limb movement index': 'OMOP:377317',
    'plm index': 'OMOP:377317',

    # Sleep parameters
    'sleep efficiency': 'OMOP:4175802',
    'sleep onset latency': 'OMOP:4175802',
    'rem latency': 'OMOP:4175802',
    'wake after sleep onset': 'OMOP:4175802',
    'waso': 'OMOP:4175802',
    'sleep stage': 'OMOP:4175802',
    'stage n1': 'OMOP:4175802',
    'stage n2': 'OMOP:4175802',
    'stage n3': 'OMOP:4175802',
    'rem sleep': 'OMOP:4175802',
    'nrem sleep': 'OMOP:4175802',

    # Oxygen
    'oxygen saturation': 'OMOP:40762499',
    'spo2': 'OMOP:40762499',
    'time below 90%': 'OMOP:40762499',
    'time below 88%': 'OMOP:40762499',
    'desaturation': 'OMOP:40762499',

    # Sleep disorders
    'obstructive sleep apnea': 'OMOP:313459',
    'central sleep apnea': 'OMOP:4145749',
    'sleep apnea': 'OMOP:313459',
    'hypopnea': 'OMOP:4151085',
    'apnea': 'OMOP:313459',
    'periodic limb movement': 'OMOP:377317',
    'restless legs syndrome': 'OMOP:377091',
    'restless leg': 'OMOP:377091',
    'narcolepsy': 'OMOP:435657',
    'insomnia': 'OMOP:435216',
    'snoring': 'OMOP:436962',
    'snore': 'OMOP:436962',

    # Sleep questionnaires
    'epworth sleepiness scale': 'OMOP:40770360',
    'epworth sleepiness': 'OMOP:40770360',
    'pittsburgh sleep quality index': 'OMOP:40770361',
    'pittsburgh sleep quality': 'OMOP:40770361',
    'psqi': 'OMOP:40770361',
    'insomnia severity index': 'OMOP:40771089',
    'functional outcomes of sleep questionnaire': 'OMOP:40770362',
    'fosq': 'OMOP:40770362',
    'berlin questionnaire': 'OMOP:40770363',
    'berlin scale': 'OMOP:40770363',
    'stop-bang': 'OMOP:40770364',
    'stopbang': 'OMOP:40770364',

    # Depression/mental health questionnaires
    'center for epidemiologic studies depression': 'OMOP:40771087',
    'ces-d': 'OMOP:40771087',
    'cesd': 'OMOP:40771087',
    'patient health questionnaire-9': 'OMOP:40771088',
    'patient health questionnaire': 'OMOP:40771088',
    'phq-9': 'OMOP:40771088',
    'phq9': 'OMOP:40771088',
    'phq-8': 'OMOP:40771088',
    'phq8': 'OMOP:40771088',
    'generalized anxiety disorder-7': 'OMOP:40771086',
    'generalized anxiety disorder': 'OMOP:40771086',
    'gad-7': 'OMOP:40771086',
    'gad7': 'OMOP:40771086',
    'beck depression inventory': 'OMOP:40771090',
    'bdi': 'OMOP:40771090',

    # QoL questionnaires
    'medical outcomes study sf-36': 'OMOP:40766968',
    'sf-36': 'OMOP:40766968',
    'sf36': 'OMOP:40766968',
    'short form 36': 'OMOP:40766968',
    'eq-5d': 'OMOP:40766969',
    'euroqol': 'OMOP:40766969',
    'child health questionnaire': 'OMOP:40766970',
    'chq': 'OMOP:40766970',
    'osa-18': 'OMOP:40770365',

    # Pediatric
    'pediatric sleep questionnaire': 'OMOP:40770367',

    # PROMIS
    'promis sleep disturbance': 'OMOP:40770366',
    'promis sleep-related impairment': 'OMOP:40770368',
    'promis sleep': 'OMOP:40770366',

    # Fatigue
    'fatigue severity scale': 'OMOP:40770369',
    'fss': 'OMOP:40770369',

    # Chronotype
    'morningness-eveningness': 'OMOP:40770370',
    'meq': 'OMOP:40770370',
    'chronotype': 'OMOP:40770370',

    # Medical conditions
    'hypertension': 'OMOP:316866',
    'high blood pressure': 'OMOP:316866',
    'diabetes mellitus': 'OMOP:201826',
    'type 2 diabetes': 'OMOP:201826',
    'diabetes': 'OMOP:201826',
    'depression': 'OMOP:440383',
    'major depressive': 'OMOP:440383',
    'anxiety disorder': 'OMOP:441542',
    'anxiety': 'OMOP:441542',
    'atrial fibrillation': 'OMOP:313217',
    'heart failure': 'OMOP:316139',
    'congestive heart failure': 'OMOP:316139',
    'stroke': 'OMOP:381591',
    'cerebrovascular': 'OMOP:381591',
    'myocardial infarction': 'OMOP:312327',
    'heart attack': 'OMOP:312327',
    'coronary artery disease': 'OMOP:318443',
    'coronary heart disease': 'OMOP:318443',
    'copd': 'OMOP:255573',
    'chronic obstructive pulmonary': 'OMOP:255573',
    'emphysema': 'OMOP:261325',
    'asthma': 'OMOP:317009',
    'chronic kidney disease': 'OMOP:46271022',
    'kidney disease': 'OMOP:46271022',
    'arthritis': 'OMOP:80809',
    'cancer': 'OMOP:443392',
    'obesity': 'OMOP:433736',

    # Treatment/Devices
    'cpap pressure': 'OMOP:4150518',
    'cpap usage': 'OMOP:4150518',
    'cpap adherence': 'OMOP:4150518',
    'cpap compliance': 'OMOP:4150518',
    'cpap': 'OMOP:4150518',

    # Actigraphy
    'actigraphy': 'OMOP:4215451',
    'activity count': 'OMOP:4215451',

    # Smoking/Alcohol
    'smoking status': 'OMOP:4041306',
    'cigarette': 'OMOP:4041306',
    'alcohol': 'OMOP:4041307',
    'caffeine': 'OMOP:4041308',
}


def get_curie(label: str) -> str:
    """Get CURIE for a label using known mappings"""
    if not label or label.strip() == '':
        return ''

    label_lower = label.lower()

    # Sort mappings by keyword length (longer = more specific = better match)
    oba_sorted = sorted(KNOWN_OBA_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)
    omop_sorted = sorted(KNOWN_OMOP_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)

    # Check OBA mappings first
    for keyword, curie in oba_sorted:
        if keyword in label_lower:
            return curie

    # Check OMOP mappings
    for keyword, curie in omop_sorted:
        if keyword in label_lower:
            return curie

    return ''


def process_tsv_file(input_file: str, output_file: str, label_col_idx: int = 2):
    """Process a TSV file and add CURIE column after variable_label"""
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile, delimiter='\t')
        rows = list(reader)

    if not rows:
        return 0, 0

    # Get header and insert CURIE column
    header = rows[0]
    new_header = header[:label_col_idx + 1] + ['CURIE'] + header[label_col_idx + 1:]

    new_rows = [new_header]
    mapped_count = 0
    total_count = 0

    for row in rows[1:]:
        label = row[label_col_idx] if len(row) > label_col_idx else ''
        curie = get_curie(label)

        if curie:
            mapped_count += 1
        total_count += 1

        new_row = row[:label_col_idx + 1] + [curie] + row[label_col_idx + 1:]
        new_rows.append(new_row)

    # Write output - overwrite original file
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        writer.writerows(new_rows)

    return mapped_count, total_count


def main():
    print("=" * 60)
    print("ADDING CURIE COLUMN TO VARIABLE TSV FILES")
    print("=" * 60)

    # Process continuous file (overwrite original)
    print("\n1. Processing continuous variables...")
    mapped, total = process_tsv_file(CONTINUOUS_FILE, CONTINUOUS_FILE, label_col_idx=2)
    print(f"   Mapped: {mapped}/{total} ({100*mapped/total:.1f}%)")

    # Process categorical file (overwrite original)
    print("\n2. Processing categorical variables...")
    mapped, total = process_tsv_file(CATEGORICAL_FILE, CATEGORICAL_FILE, label_col_idx=2)
    print(f"   Mapped: {mapped}/{total} ({100*mapped/total:.1f}%)")

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
