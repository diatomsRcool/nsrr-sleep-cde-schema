#!/usr/bin/env python3
"""
Update CURIEs for Condition rows (Mondo/HPO) and DrugExposure rows (RxNorm).
"""

import csv
import re
from typing import Optional

# File paths
CONTINUOUS_FILE = '/Users/athessen/sleep-cde-schema/continuous_variables_cde_updated.tsv'
CATEGORICAL_FILE = '/Users/athessen/sleep-cde-schema/categorical_variables_cde_updated.tsv'

# Mondo mappings for conditions (diseases/disorders)
# Format: keyword -> MONDO:xxxxxxx or HP:xxxxxxx
MONDO_MAPPINGS = {
    # Sleep disorders
    'obstructive sleep apnea': 'MONDO:0007147',
    'sleep apnea': 'MONDO:0005296',
    'central sleep apnea': 'MONDO:0000958',
    'insomnia': 'MONDO:0013600',
    'narcolepsy': 'MONDO:0016158',
    'restless legs syndrome': 'MONDO:0005306',
    'restless leg syndrome': 'MONDO:0005306',
    'periodic limb movement disorder': 'MONDO:0011997',
    'hypersomnia': 'MONDO:0016022',
    'circadian rhythm disorder': 'MONDO:0012114',
    'sleep disorder': 'MONDO:0005316',
    'parasomnia': 'MONDO:0002241',
    'sleepwalking': 'MONDO:0001575',
    'sleep terror': 'MONDO:0001706',
    'rem sleep behavior disorder': 'MONDO:0011704',
    'bruxism': 'MONDO:0002439',

    # Cardiovascular
    'hypertension': 'MONDO:0005044',
    'high blood pressure': 'MONDO:0005044',
    'atrial fibrillation': 'MONDO:0004981',
    'heart failure': 'MONDO:0005009',
    'congestive heart failure': 'MONDO:0005009',
    'coronary artery disease': 'MONDO:0005010',
    'coronary heart disease': 'MONDO:0005010',
    'myocardial infarction': 'MONDO:0005068',
    'heart attack': 'MONDO:0005068',
    'stroke': 'MONDO:0005098',
    'cerebrovascular disease': 'MONDO:0005098',
    'arrhythmia': 'MONDO:0003045',
    'angina': 'MONDO:0002604',
    'atherosclerosis': 'MONDO:0005311',
    'pulmonary hypertension': 'MONDO:0005149',
    'peripheral vascular disease': 'MONDO:0005294',
    'deep vein thrombosis': 'MONDO:0005083',
    'pulmonary embolism': 'MONDO:0005279',

    # Metabolic/Endocrine
    'diabetes': 'MONDO:0005015',
    'type 2 diabetes': 'MONDO:0005148',
    'type 1 diabetes': 'MONDO:0005147',
    'obesity': 'MONDO:0011122',
    'metabolic syndrome': 'MONDO:0005148',
    'hyperlipidemia': 'MONDO:0002525',
    'dyslipidemia': 'MONDO:0002525',
    'high cholesterol': 'MONDO:0002525',
    'hyperthyroidism': 'MONDO:0004425',
    'hypothyroidism': 'MONDO:0005420',
    'thyroid disease': 'MONDO:0003240',
    'gout': 'MONDO:0005393',

    # Respiratory
    'asthma': 'MONDO:0004979',
    'copd': 'MONDO:0005002',
    'chronic obstructive pulmonary disease': 'MONDO:0005002',
    'emphysema': 'MONDO:0002087',
    'chronic bronchitis': 'MONDO:0003783',
    'pulmonary fibrosis': 'MONDO:0005402',
    'pneumonia': 'MONDO:0005249',

    # Mental health
    'depression': 'MONDO:0002050',
    'major depressive disorder': 'MONDO:0002050',
    'anxiety': 'MONDO:0005618',
    'anxiety disorder': 'MONDO:0005618',
    'bipolar disorder': 'MONDO:0004985',
    'schizophrenia': 'MONDO:0005090',
    'ptsd': 'MONDO:0005146',
    'post-traumatic stress disorder': 'MONDO:0005146',
    'adhd': 'MONDO:0007743',
    'attention deficit': 'MONDO:0007743',

    # Neurological
    'epilepsy': 'MONDO:0005027',
    'seizure': 'HP:0001250',
    'migraine': 'MONDO:0005277',
    'parkinson': 'MONDO:0005180',
    'alzheimer': 'MONDO:0004975',
    'dementia': 'MONDO:0001627',
    'multiple sclerosis': 'MONDO:0005301',
    'neuropathy': 'MONDO:0005244',

    # Renal
    'chronic kidney disease': 'MONDO:0005300',
    'kidney disease': 'MONDO:0005300',
    'renal disease': 'MONDO:0005300',
    'end-stage renal disease': 'MONDO:0005300',

    # Gastrointestinal
    'gerd': 'MONDO:0007186',
    'gastroesophageal reflux': 'MONDO:0007186',
    'acid reflux': 'MONDO:0007186',
    'liver disease': 'MONDO:0005154',
    'hepatitis': 'MONDO:0005260',
    'cirrhosis': 'MONDO:0005155',
    'fatty liver': 'MONDO:0004790',
    'inflammatory bowel disease': 'MONDO:0005265',
    'crohn': 'MONDO:0005011',
    'ulcerative colitis': 'MONDO:0005101',
    'irritable bowel syndrome': 'MONDO:0006574',

    # Musculoskeletal
    'arthritis': 'MONDO:0005160',
    'rheumatoid arthritis': 'MONDO:0008383',
    'osteoarthritis': 'MONDO:0005178',
    'osteoporosis': 'MONDO:0005298',
    'fibromyalgia': 'MONDO:0005546',

    # Cancer
    'cancer': 'MONDO:0004992',
    'malignancy': 'MONDO:0004992',
    'tumor': 'MONDO:0004992',
    'neoplasm': 'MONDO:0004992',
    'breast cancer': 'MONDO:0007254',
    'lung cancer': 'MONDO:0008903',
    'prostate cancer': 'MONDO:0008315',
    'colon cancer': 'MONDO:0005575',
    'colorectal cancer': 'MONDO:0005575',

    # ENT
    'sinusitis': 'MONDO:0005608',
    'hay fever': 'MONDO:0004991',
    'allergic rhinitis': 'MONDO:0004991',
    'nasal congestion': 'HP:0001742',
    'tonsillitis': 'MONDO:0005776',

    # Skin
    'eczema': 'MONDO:0004980',
    'psoriasis': 'MONDO:0005083',
    'dermatitis': 'MONDO:0002406',

    # Other
    'anemia': 'MONDO:0002280',
    'chronic fatigue syndrome': 'MONDO:0005404',

    # Additional mappings
    'ischemic heart disease': 'MONDO:0004995',
    'valvular heart disease': 'MONDO:0005181',
    'rheumatic heart disease': 'MONDO:0005249',
    'periodontal disease': 'MONDO:0005109',
    'thyroid problem': 'MONDO:0003240',
    'heartburn': 'MONDO:0007186',
    'obstructive lung disease': 'MONDO:0005002',
    'pulmonary disease': 'MONDO:0005275',
    'severe pulmonary disease': 'MONDO:0005275',
    'heart disease': 'MONDO:0005267',
    'elevated cholesterol': 'MONDO:0002525',
}

# RxNorm mappings for drugs
# Format: keyword -> RxNorm:xxxxxxx
RXNORM_MAPPINGS = {
    # Antihypertensives
    'antihypertensive': 'RxNorm:48940',  # Antihypertensive agents [TC]
    'ace inhibitor': 'RxNorm:36044',
    'beta blocker': 'RxNorm:6918',
    'beta-blocker': 'RxNorm:6918',
    'calcium channel blocker': 'RxNorm:20352',
    'diuretic': 'RxNorm:49217',
    'thiazide': 'RxNorm:37984',
    'amlodipine': 'RxNorm:17767',
    'lisinopril': 'RxNorm:29046',
    'losartan': 'RxNorm:52175',
    'metoprolol': 'RxNorm:6918',
    'atenolol': 'RxNorm:1202',

    # Lipid-lowering
    'statin': 'RxNorm:41127',
    'atorvastatin': 'RxNorm:83367',
    'simvastatin': 'RxNorm:36567',
    'rosuvastatin': 'RxNorm:301542',
    'pravastatin': 'RxNorm:42463',
    'lipid-lowering': 'RxNorm:41127',

    # Diabetes medications
    'insulin': 'RxNorm:5856',
    'metformin': 'RxNorm:6809',
    'sulfonylurea': 'RxNorm:39786',
    'glipizide': 'RxNorm:4821',
    'glyburide': 'RxNorm:4815',
    'sitagliptin': 'RxNorm:593411',
    'empagliflozin': 'RxNorm:1545653',

    # Anticoagulants/Antiplatelets
    'aspirin': 'RxNorm:1191',
    'warfarin': 'RxNorm:11289',
    'clopidogrel': 'RxNorm:32968',
    'plavix': 'RxNorm:32968',
    'anticoagulant': 'RxNorm:68461',
    'antiplatelet': 'RxNorm:48344',

    # Sedatives/Hypnotics
    'benzodiazepine': 'RxNorm:3322',
    'sedative': 'RxNorm:35794',
    'hypnotic': 'RxNorm:35794',
    'sleeping pill': 'RxNorm:35794',
    'zolpidem': 'RxNorm:39993',
    'ambien': 'RxNorm:39993',
    'temazepam': 'RxNorm:10355',
    'lorazepam': 'RxNorm:6470',
    'alprazolam': 'RxNorm:596',
    'diazepam': 'RxNorm:3322',
    'clonazepam': 'RxNorm:2598',
    'eszopiclone': 'RxNorm:308986',
    'lunesta': 'RxNorm:308986',
    'trazodone': 'RxNorm:10737',
    'melatonin': 'RxNorm:6719',

    # Antidepressants
    'antidepressant': 'RxNorm:47562',
    'ssri': 'RxNorm:47562',
    'sertraline': 'RxNorm:36437',
    'fluoxetine': 'RxNorm:4493',
    'citalopram': 'RxNorm:2556',
    'escitalopram': 'RxNorm:321988',
    'paroxetine': 'RxNorm:32937',
    'venlafaxine': 'RxNorm:39786',
    'duloxetine': 'RxNorm:72625',
    'bupropion': 'RxNorm:42347',
    'amitriptyline': 'RxNorm:704',
    'mirtazapine': 'RxNorm:30121',

    # Anxiolytics
    'anxiolytic': 'RxNorm:N0000175573',
    'buspirone': 'RxNorm:1827',

    # Respiratory medications
    'bronchodilator': 'RxNorm:48166',
    'albuterol': 'RxNorm:435',
    'inhaler': 'RxNorm:48166',
    'inhaled corticosteroid': 'RxNorm:51499',
    'fluticasone': 'RxNorm:41126',
    'budesonide': 'RxNorm:19831',
    'montelukast': 'RxNorm:88249',
    'singulair': 'RxNorm:88249',

    # Pain medications
    'opioid': 'RxNorm:7814',
    'acetaminophen': 'RxNorm:161',
    'tylenol': 'RxNorm:161',
    'ibuprofen': 'RxNorm:5640',
    'nsaid': 'RxNorm:35827',
    'naproxen': 'RxNorm:7258',
    'tramadol': 'RxNorm:10689',
    'gabapentin': 'RxNorm:25480',
    'pregabalin': 'RxNorm:187832',
    'lyrica': 'RxNorm:187832',

    # Thyroid
    'levothyroxine': 'RxNorm:10582',
    'synthroid': 'RxNorm:10582',
    'thyroid medication': 'RxNorm:10582',

    # GI medications
    'proton pump inhibitor': 'RxNorm:31739',
    'ppi': 'RxNorm:31739',
    'omeprazole': 'RxNorm:7646',
    'pantoprazole': 'RxNorm:40790',
    'esomeprazole': 'RxNorm:283742',
    'h2 blocker': 'RxNorm:35829',
    'antacid': 'RxNorm:51499',

    # ADHD medications
    'stimulant': 'RxNorm:N0000175711',
    'methylphenidate': 'RxNorm:6901',
    'ritalin': 'RxNorm:6901',
    'adderall': 'RxNorm:725',
    'amphetamine': 'RxNorm:725',

    # Antipsychotics
    'antipsychotic': 'RxNorm:N0000175752',
    'quetiapine': 'RxNorm:51272',
    'seroquel': 'RxNorm:51272',
    'risperidone': 'RxNorm:35636',
    'olanzapine': 'RxNorm:61381',

    # Antihistamines
    'antihistamine': 'RxNorm:N0000175564',
    'diphenhydramine': 'RxNorm:3498',
    'benadryl': 'RxNorm:3498',
    'cetirizine': 'RxNorm:20610',
    'loratadine': 'RxNorm:26225',

    # Misc
    'vitamin': 'RxNorm:N0000181144',
    'supplement': 'RxNorm:N0000009946',
    'herbal': 'RxNorm:N0000009946',

    # Additional specific mappings
    'adhd_medication': 'RxNorm:6901',  # methylphenidate class
    'anxiety_medication': 'RxNorm:N0000175573',
    'depression_medication': 'RxNorm:47562',
    'eczema_medication': 'RxNorm:N0000175636',  # topical corticosteroids
    'hay_fever_medication': 'RxNorm:N0000175564',  # antihistamine
    'high_bp_medication': 'RxNorm:48940',
    'high_chol_medication': 'RxNorm:41127',
    'insomnia_medication': 'RxNorm:35794',
    'migraine_medication': 'RxNorm:N0000175707',
    'illicit': 'RxNorm:N0000175756',
}


def get_mondo_hpo_curie(label: str) -> Optional[str]:
    """Get Mondo/HPO CURIE for a condition label"""
    if not label:
        return None

    label_lower = label.lower()

    # Sort by length (longer matches first for specificity)
    sorted_mappings = sorted(MONDO_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)

    for keyword, curie in sorted_mappings:
        if keyword in label_lower:
            return curie

    return None


def get_rxnorm_curie(label: str) -> Optional[str]:
    """Get RxNorm CURIE for a drug exposure label"""
    if not label:
        return None

    label_lower = label.lower()

    # Sort by length (longer matches first for specificity)
    sorted_mappings = sorted(RXNORM_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)

    for keyword, curie in sorted_mappings:
        if keyword in label_lower:
            return curie

    return None


def process_tsv_file(input_file: str):
    """Process a TSV file and update CURIEs for Condition and DrugExposure rows"""
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile, delimiter='\t')
        rows = list(reader)

    if not rows:
        return 0, 0, 0, 0

    header = rows[0]

    # Find column indices
    bdchm_idx = header.index('bdchm_class')
    curie_idx = header.index('CURIE')
    label_idx = header.index('variable_label')

    condition_updated = 0
    condition_total = 0
    drug_updated = 0
    drug_total = 0

    for row in rows[1:]:
        if len(row) <= max(bdchm_idx, curie_idx, label_idx):
            continue

        bdchm_class = row[bdchm_idx]
        label = row[label_idx]

        if bdchm_class == 'Condition':
            condition_total += 1
            new_curie = get_mondo_hpo_curie(label)
            if new_curie:
                row[curie_idx] = new_curie
                condition_updated += 1

        elif bdchm_class == 'DrugExposure':
            drug_total += 1
            new_curie = get_rxnorm_curie(label)
            if new_curie:
                row[curie_idx] = new_curie
                drug_updated += 1

    # Write output
    with open(input_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        writer.writerows(rows)

    return condition_updated, condition_total, drug_updated, drug_total


def main():
    print("=" * 60)
    print("UPDATING CURIEs FOR CONDITION AND DRUGEXPOSURE ROWS")
    print("=" * 60)

    # Process continuous file
    print("\n1. Processing continuous variables...")
    c_cond, c_cond_tot, c_drug, c_drug_tot = process_tsv_file(CONTINUOUS_FILE)
    print(f"   Conditions: {c_cond}/{c_cond_tot} updated with Mondo/HPO")
    print(f"   DrugExposures: {c_drug}/{c_drug_tot} updated with RxNorm")

    # Process categorical file
    print("\n2. Processing categorical variables...")
    cat_cond, cat_cond_tot, cat_drug, cat_drug_tot = process_tsv_file(CATEGORICAL_FILE)
    print(f"   Conditions: {cat_cond}/{cat_cond_tot} updated with Mondo/HPO")
    print(f"   DrugExposures: {cat_drug}/{cat_drug_tot} updated with RxNorm")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Conditions updated: {c_cond + cat_cond}/{c_cond_tot + cat_cond_tot}")
    print(f"Total DrugExposures updated: {c_drug + cat_drug}/{c_drug_tot + cat_drug_tot}")


if __name__ == "__main__":
    main()
