#!/usr/bin/env python3
"""
Add bdchm_class column to variable TSV files.
Classifies variables according to BioData Catalyst Harmonized Model (BDCHM) elements.

BDCHM Classes (from https://github.com/RTIInternational/NHLBI-BDC-DMC-HM):
- Person: Basic person info
- Demography: Demographics (age, sex, race, ethnicity, education)
- Participant: Study participant info
- ResearchStudy: Study metadata
- Visit: Study visits/timepoints
- Questionnaire: Survey instruments
- QuestionnaireResponse: Survey responses
- Condition: Medical conditions/diagnoses
- Procedure: Medical procedures
- DrugExposure: Medications
- DeviceExposure: Medical devices (CPAP, etc.)
- MeasurementObservation: Measurements (labs, vitals, PSG metrics)
- SdohObservation: Social determinants of health
- Exposure: Environmental/behavioral exposures
- Specimen: Biological specimens
- CauseOfDeath: Mortality info
"""

import csv
import re
from typing import Optional

# File paths
CONTINUOUS_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'
CATEGORICAL_FILE = '/Users/athessen/sleep-cde-schema/categorical_variables_cde_updated.tsv'

# BDCHM classification keywords (sorted by specificity - longer/more specific first)
# Each tuple is (keyword, bdchm_class)

BDCHM_KEYWORDS = [
    # Demography - demographics come first (age, sex, race, etc.)
    ('age at ', 'Demography'),
    ('age of ', 'Demography'),
    ('age (', 'Demography'),
    ('age in years', 'Demography'),
    ('age greater than', 'Demography'),
    ('sex', 'Demography'),
    ('gender', 'Demography'),
    ('race', 'Demography'),
    ('ethnicity', 'Demography'),
    ('hispanic', 'Demography'),
    ('latino', 'Demography'),
    ('education', 'Demography'),
    ('marital status', 'Demography'),
    ('employment', 'Demography'),
    ('occupation', 'Demography'),
    ('income', 'Demography'),
    ('birth', 'Demography'),
    ('language', 'Demography'),

    # Visit/Study - study visits and timepoints
    ('visit', 'Visit'),
    ('follow-up', 'Visit'),
    ('followup', 'Visit'),
    ('baseline', 'Visit'),
    ('screening', 'Visit'),
    ('timepoint', 'Visit'),
    ('exam ', 'Visit'),
    ('randomization', 'Visit'),

    # Questionnaire/QuestionnaireResponse - survey instruments
    ('epworth sleepiness scale', 'QuestionnaireResponse'),
    ('pittsburgh sleep quality', 'QuestionnaireResponse'),
    ('insomnia severity index', 'QuestionnaireResponse'),
    ('berlin questionnaire', 'QuestionnaireResponse'),
    ('stop-bang', 'QuestionnaireResponse'),
    ('center for epidemiologic studies depression', 'QuestionnaireResponse'),
    ('patient health questionnaire', 'QuestionnaireResponse'),
    ('generalized anxiety disorder', 'QuestionnaireResponse'),
    ('beck depression', 'QuestionnaireResponse'),
    ('sf-36', 'QuestionnaireResponse'),
    ('sf36', 'QuestionnaireResponse'),
    ('short form 36', 'QuestionnaireResponse'),
    ('eq-5d', 'QuestionnaireResponse'),
    ('euroqol', 'QuestionnaireResponse'),
    ('child health questionnaire', 'QuestionnaireResponse'),
    ('osa-18', 'QuestionnaireResponse'),
    ('promis sleep', 'QuestionnaireResponse'),
    ('fatigue severity scale', 'QuestionnaireResponse'),
    ('functional outcomes of sleep', 'QuestionnaireResponse'),
    ('fosq', 'QuestionnaireResponse'),
    ('morningness-eveningness', 'QuestionnaireResponse'),
    ('chronotype', 'QuestionnaireResponse'),
    ('pediatric sleep questionnaire', 'QuestionnaireResponse'),
    ('quality of life', 'QuestionnaireResponse'),
    ('psqi', 'QuestionnaireResponse'),
    ('phq-9', 'QuestionnaireResponse'),
    ('phq9', 'QuestionnaireResponse'),
    ('phq-8', 'QuestionnaireResponse'),
    ('gad-7', 'QuestionnaireResponse'),
    ('gad7', 'QuestionnaireResponse'),
    ('ces-d', 'QuestionnaireResponse'),
    ('cesd', 'QuestionnaireResponse'),
    ('ess ', 'QuestionnaireResponse'),
    ('bdi', 'QuestionnaireResponse'),
    ('scale:', 'QuestionnaireResponse'),
    ('questionnaire', 'QuestionnaireResponse'),
    ('survey', 'QuestionnaireResponse'),
    ('self-report', 'QuestionnaireResponse'),
    ('self report', 'QuestionnaireResponse'),

    # Condition - medical conditions/diagnoses
    ('obstructive sleep apnea', 'Condition'),
    ('central sleep apnea', 'Condition'),
    ('sleep apnea', 'Condition'),
    ('insomnia diagnosis', 'Condition'),
    ('narcolepsy', 'Condition'),
    ('restless legs syndrome', 'Condition'),
    ('restless leg syndrome', 'Condition'),
    ('hypertension', 'Condition'),
    ('high blood pressure', 'Condition'),
    ('diabetes', 'Condition'),
    ('heart failure', 'Condition'),
    ('atrial fibrillation', 'Condition'),
    ('coronary artery disease', 'Condition'),
    ('coronary heart disease', 'Condition'),
    ('myocardial infarction', 'Condition'),
    ('heart attack', 'Condition'),
    ('stroke', 'Condition'),
    ('cerebrovascular', 'Condition'),
    ('copd', 'Condition'),
    ('chronic obstructive pulmonary', 'Condition'),
    ('emphysema', 'Condition'),
    ('asthma', 'Condition'),
    ('depression diagnosis', 'Condition'),
    ('anxiety disorder', 'Condition'),
    ('cancer', 'Condition'),
    ('arthritis', 'Condition'),
    ('kidney disease', 'Condition'),
    ('liver disease', 'Condition'),
    ('thyroid', 'Condition'),
    ('obesity', 'Condition'),
    ('diagnosis', 'Condition'),
    ('diagnosed', 'Condition'),
    ('history of', 'Condition'),
    ('ever had', 'Condition'),
    ('comorbid', 'Condition'),
    ('disease', 'Condition'),

    # DrugExposure - medications
    ('medication', 'DrugExposure'),
    ('drug', 'DrugExposure'),
    ('prescription', 'DrugExposure'),
    ('anti-hypertensive', 'DrugExposure'),
    ('antihypertensive', 'DrugExposure'),
    ('beta-blocker', 'DrugExposure'),
    ('beta blocker', 'DrugExposure'),
    ('diuretic', 'DrugExposure'),
    ('statin', 'DrugExposure'),
    ('lipid-lowering', 'DrugExposure'),
    ('benzodiazepine', 'DrugExposure'),
    ('sedative', 'DrugExposure'),
    ('hypnotic', 'DrugExposure'),
    ('sleeping pill', 'DrugExposure'),
    ('antidepressant', 'DrugExposure'),
    ('anti-depressant', 'DrugExposure'),
    ('aspirin', 'DrugExposure'),
    ('insulin', 'DrugExposure'),
    ('metformin', 'DrugExposure'),
    ('bronchodilator', 'DrugExposure'),

    # DeviceExposure - medical devices
    ('cpap', 'DeviceExposure'),
    ('bipap', 'DeviceExposure'),
    ('apap', 'DeviceExposure'),
    ('positive airway pressure', 'DeviceExposure'),
    ('pap therapy', 'DeviceExposure'),
    ('pap device', 'DeviceExposure'),
    ('pap adherence', 'DeviceExposure'),
    ('pap compliance', 'DeviceExposure'),
    ('oral appliance', 'DeviceExposure'),
    ('dental device', 'DeviceExposure'),
    ('mask', 'DeviceExposure'),
    ('pacemaker', 'DeviceExposure'),

    # Procedure - medical procedures
    ('surgery', 'Procedure'),
    ('surgical', 'Procedure'),
    ('procedure', 'Procedure'),
    ('adenotonsillectomy', 'Procedure'),
    ('tonsillectomy', 'Procedure'),
    ('uvulopalatopharyngoplasty', 'Procedure'),
    ('uppp', 'Procedure'),
    ('bariatric', 'Procedure'),
    ('ablation', 'Procedure'),
    ('titration', 'Procedure'),
    ('split-night', 'Procedure'),
    ('polysomnography study', 'Procedure'),

    # Exposure - behavioral/environmental exposures
    ('smoking', 'Exposure'),
    ('cigarette', 'Exposure'),
    ('tobacco', 'Exposure'),
    ('alcohol', 'Exposure'),
    ('caffeine', 'Exposure'),
    ('coffee', 'Exposure'),
    ('pack-years', 'Exposure'),
    ('pack years', 'Exposure'),
    ('secondhand smoke', 'Exposure'),
    ('environmental', 'Exposure'),

    # SdohObservation - social determinants of health
    ('housing', 'SdohObservation'),
    ('neighborhood', 'SdohObservation'),
    ('food insecurity', 'SdohObservation'),
    ('food security', 'SdohObservation'),
    ('transportation', 'SdohObservation'),
    ('social support', 'SdohObservation'),
    ('discrimination', 'SdohObservation'),
    ('stress', 'SdohObservation'),
    ('socioeconomic', 'SdohObservation'),

    # Specimen - biological specimens
    ('blood sample', 'Specimen'),
    ('urine sample', 'Specimen'),
    ('specimen', 'Specimen'),
    ('biospecimen', 'Specimen'),
    ('sample collection', 'Specimen'),

    # CauseOfDeath - mortality
    ('cause of death', 'CauseOfDeath'),
    ('mortality', 'CauseOfDeath'),
    ('death', 'CauseOfDeath'),
    ('deceased', 'CauseOfDeath'),
    ('vital status', 'CauseOfDeath'),

    # MeasurementObservation - measurements (this is the catch-all for most sleep study data)
    # Sleep study measurements
    ('apnea-hypopnea index', 'MeasurementObservation'),
    ('apnea hypopnea index', 'MeasurementObservation'),
    ('respiratory disturbance index', 'MeasurementObservation'),
    ('oxygen desaturation index', 'MeasurementObservation'),
    ('arousal index', 'MeasurementObservation'),
    ('periodic limb movement', 'MeasurementObservation'),
    ('plm index', 'MeasurementObservation'),
    ('sleep efficiency', 'MeasurementObservation'),
    ('sleep latency', 'MeasurementObservation'),
    ('rem latency', 'MeasurementObservation'),
    ('total sleep time', 'MeasurementObservation'),
    ('sleep duration', 'MeasurementObservation'),
    ('wake after sleep onset', 'MeasurementObservation'),
    ('waso', 'MeasurementObservation'),
    ('time in bed', 'MeasurementObservation'),
    ('sleep stage', 'MeasurementObservation'),
    ('stage n1', 'MeasurementObservation'),
    ('stage n2', 'MeasurementObservation'),
    ('stage n3', 'MeasurementObservation'),
    ('rem sleep', 'MeasurementObservation'),
    ('nrem sleep', 'MeasurementObservation'),
    ('oxygen saturation', 'MeasurementObservation'),
    ('spo2', 'MeasurementObservation'),
    ('desaturation', 'MeasurementObservation'),
    ('hypopnea', 'MeasurementObservation'),
    ('apnea', 'MeasurementObservation'),
    ('snoring', 'MeasurementObservation'),
    ('snore', 'MeasurementObservation'),

    # Anthropometry
    ('body mass index', 'MeasurementObservation'),
    ('bmi', 'MeasurementObservation'),
    ('height', 'MeasurementObservation'),
    ('weight', 'MeasurementObservation'),
    ('waist circumference', 'MeasurementObservation'),
    ('hip circumference', 'MeasurementObservation'),
    ('neck circumference', 'MeasurementObservation'),

    # Vital signs
    ('blood pressure', 'MeasurementObservation'),
    ('systolic', 'MeasurementObservation'),
    ('diastolic', 'MeasurementObservation'),
    ('heart rate', 'MeasurementObservation'),
    ('pulse', 'MeasurementObservation'),
    ('respiratory rate', 'MeasurementObservation'),
    ('temperature', 'MeasurementObservation'),

    # Lab values
    ('glucose', 'MeasurementObservation'),
    ('cholesterol', 'MeasurementObservation'),
    ('triglyceride', 'MeasurementObservation'),
    ('hemoglobin', 'MeasurementObservation'),
    ('hba1c', 'MeasurementObservation'),
    ('hematocrit', 'MeasurementObservation'),
    ('creatinine', 'MeasurementObservation'),
    ('albumin', 'MeasurementObservation'),
    ('bilirubin', 'MeasurementObservation'),
    ('c-reactive protein', 'MeasurementObservation'),
    ('crp', 'MeasurementObservation'),
    ('ferritin', 'MeasurementObservation'),
    ('insulin level', 'MeasurementObservation'),
    ('thyroid', 'MeasurementObservation'),
    ('tsh', 'MeasurementObservation'),
    ('ldl', 'MeasurementObservation'),
    ('hdl', 'MeasurementObservation'),

    # Spirometry
    ('fev1', 'MeasurementObservation'),
    ('fev 1', 'MeasurementObservation'),
    ('fvc', 'MeasurementObservation'),
    ('forced vital capacity', 'MeasurementObservation'),
    ('forced expiratory', 'MeasurementObservation'),
    ('spirometry', 'MeasurementObservation'),

    # HRV
    ('heart rate variability', 'MeasurementObservation'),
    ('hrv', 'MeasurementObservation'),
    ('sdnn', 'MeasurementObservation'),
    ('rmssd', 'MeasurementObservation'),

    # Actigraphy
    ('actigraphy', 'MeasurementObservation'),
    ('activity count', 'MeasurementObservation'),
    ('actogram', 'MeasurementObservation'),

    # Polysomnography
    ('polysomnography', 'MeasurementObservation'),
    ('psg', 'MeasurementObservation'),
    ('eeg', 'MeasurementObservation'),
    ('emg', 'MeasurementObservation'),
    ('eog', 'MeasurementObservation'),
    ('ecg', 'MeasurementObservation'),

    # Cognitive tests
    ('psychomotor vigilance', 'MeasurementObservation'),
    ('pvt', 'MeasurementObservation'),
    ('reaction time', 'MeasurementObservation'),
    ('cognitive', 'MeasurementObservation'),

    # More lab values / biomarkers
    ('adiponectin', 'MeasurementObservation'),
    ('ghrelin', 'MeasurementObservation'),
    ('leptin', 'MeasurementObservation'),
    ('fibrinogen', 'MeasurementObservation'),
    ('interleukin', 'MeasurementObservation'),
    ('il-6', 'MeasurementObservation'),
    ('il-1', 'MeasurementObservation'),
    ('tnf', 'MeasurementObservation'),
    ('tumor necrosis', 'MeasurementObservation'),
    ('cortisol', 'MeasurementObservation'),
    ('melatonin', 'MeasurementObservation'),
    ('epinephrine', 'MeasurementObservation'),
    ('norepinephrine', 'MeasurementObservation'),
    ('catecholamine', 'MeasurementObservation'),
    ('homocysteine', 'MeasurementObservation'),
    ('uric acid', 'MeasurementObservation'),
    ('potassium', 'MeasurementObservation'),
    ('sodium', 'MeasurementObservation'),
    ('calcium', 'MeasurementObservation'),
    ('magnesium', 'MeasurementObservation'),
    ('phosphorus', 'MeasurementObservation'),
    ('bicarbonate', 'MeasurementObservation'),
    ('chloride', 'MeasurementObservation'),
    ('protein', 'MeasurementObservation'),
    ('bnp', 'MeasurementObservation'),
    ('troponin', 'MeasurementObservation'),
    ('procalcitonin', 'MeasurementObservation'),
    ('d-dimer', 'MeasurementObservation'),
    ('white blood cell', 'MeasurementObservation'),
    ('wbc', 'MeasurementObservation'),
    ('red blood cell', 'MeasurementObservation'),
    ('rbc', 'MeasurementObservation'),
    ('platelet', 'MeasurementObservation'),
    ('neutrophil', 'MeasurementObservation'),
    ('lymphocyte', 'MeasurementObservation'),
    ('monocyte', 'MeasurementObservation'),
    ('eosinophil', 'MeasurementObservation'),
    ('basophil', 'MeasurementObservation'),
    ('alt', 'MeasurementObservation'),
    ('ast', 'MeasurementObservation'),
    ('ggt', 'MeasurementObservation'),
    ('alkaline phosphatase', 'MeasurementObservation'),
    ('lipase', 'MeasurementObservation'),
    ('amylase', 'MeasurementObservation'),
    ('homa', 'MeasurementObservation'),

    # Participant/Study identifiers
    ('participant id', 'Participant'),
    ('subject id', 'Participant'),
    ('study id', 'Participant'),
    ('patient id', 'Participant'),
    ('namecode', 'Participant'),
    ('id number', 'Participant'),
    ('file id', 'Participant'),

    # ResearchStudy
    ('study name', 'ResearchStudy'),
    ('study site', 'ResearchStudy'),
    ('center', 'ResearchStudy'),
    ('cohort', 'ResearchStudy'),
    ('treatment arm', 'ResearchStudy'),
    ('randomized', 'ResearchStudy'),
    ('eligibility', 'ResearchStudy'),
    ('consent', 'ResearchStudy'),
    ('enrollment', 'ResearchStudy'),

    # Generic measurement indicators
    ('index', 'MeasurementObservation'),
    ('score', 'MeasurementObservation'),
    ('count', 'MeasurementObservation'),
    ('duration', 'MeasurementObservation'),
    ('percentage', 'MeasurementObservation'),
    ('percent', 'MeasurementObservation'),
    ('average', 'MeasurementObservation'),
    ('mean', 'MeasurementObservation'),
    ('median', 'MeasurementObservation'),
    ('minimum', 'MeasurementObservation'),
    ('maximum', 'MeasurementObservation'),
    ('total', 'MeasurementObservation'),
    ('number of', 'MeasurementObservation'),
    ('ratio', 'MeasurementObservation'),
    ('level', 'MeasurementObservation'),
    ('concentration', 'MeasurementObservation'),
    ('measurement', 'MeasurementObservation'),
    ('value', 'MeasurementObservation'),
    ('rate', 'MeasurementObservation'),
    ('time', 'MeasurementObservation'),
]


def get_bdchm_class(label: str) -> str:
    """Get BDCHM class for a variable label"""
    if not label or label.strip() == '':
        return ''

    label_lower = label.lower()

    # Check keywords in order (already sorted by specificity in the list)
    for keyword, bdchm_class in BDCHM_KEYWORDS:
        if keyword in label_lower:
            return bdchm_class

    return ''


def process_tsv_file(input_file: str, label_col_idx: int = 2, curie_col_idx: int = 3):
    """Process a TSV file and add bdchm_class column before CURIE"""
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile, delimiter='\t')
        rows = list(reader)

    if not rows:
        return 0, 0

    # Get header and insert bdchm_class column before CURIE
    header = rows[0]
    new_header = header[:curie_col_idx] + ['bdchm_class'] + header[curie_col_idx:]

    new_rows = [new_header]
    classified_count = 0
    total_count = 0

    for row in rows[1:]:
        label = row[label_col_idx] if len(row) > label_col_idx else ''
        bdchm_class = get_bdchm_class(label)

        if bdchm_class:
            classified_count += 1
        total_count += 1

        new_row = row[:curie_col_idx] + [bdchm_class] + row[curie_col_idx:]
        new_rows.append(new_row)

    # Write output - overwrite original file
    with open(input_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        writer.writerows(new_rows)

    return classified_count, total_count


def main():
    print("=" * 60)
    print("ADDING BDCHM CLASS COLUMN TO VARIABLE TSV FILES")
    print("=" * 60)

    # Process continuous file
    print("\n1. Processing continuous variables...")
    # In continuous file: study_name(0), variable_name(1), variable_label(2), CURIE(3), folder(4)...
    classified, total = process_tsv_file(CONTINUOUS_FILE, label_col_idx=2, curie_col_idx=3)
    print(f"   Classified: {classified}/{total} ({100*classified/total:.1f}%)")

    # Process categorical file
    print("\n2. Processing categorical variables...")
    # In categorical file: study_name(0), variable_name(1), variable_label(2), CURIE(3), folder(4)...
    classified, total = process_tsv_file(CATEGORICAL_FILE, label_col_idx=2, curie_col_idx=3)
    print(f"   Classified: {classified}/{total} ({100*classified/total:.1f}%)")

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
