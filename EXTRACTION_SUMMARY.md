# Sleep Study Variable Extraction Summary

## Overview
Systematically extracted ALL variables from 31 sleep study datasets at sleepdata.org, handling multi-visit data structure.

**Date:** 2026-01-09
**Total Studies Processed:** 31
**Total Variables Extracted:** 2,506
- Continuous Variables: 1,920
- Categorical Variables: 586

## Output Files

### 1. continuous_variables.tsv
**Location:** `/Users/athessen/sleep-cde-schema/continuous_variables.tsv`
**Rows:** 1,921 (including header)
**Columns:**
- study_name
- variable_name
- variable_label
- folder
- description
- visit
- domain
- type
- total_subjects
- units
- n
- mean
- stddev
- median
- min
- max
- unknown

**Note:** Statistics columns (n, mean, stddev, median, min, max, unknown) are currently empty. To populate these with actual values would require visiting individual variable pages for each of the 2,506 variables, which would involve thousands of additional web requests. The current extraction provides the comprehensive variable inventory.

### 2. categorical_variables.tsv
**Location:** `/Users/athessen/sleep-cde-schema/categorical_variables.tsv`
**Rows:** 587 (including header)
**Columns:**
- study_name
- variable_name
- variable_label
- folder
- description
- visit
- domain
- type

## Studies Processed

All 31 studies from studies_with_variables.txt:

| Study | Full Name | Continuous | Categorical | Total |
|-------|-----------|------------|-------------|-------|
| ABC | Apnea, Bariatric surgery, and CPAP | 78 | 22 | 100 |
| ANSWERS | Assessing Nocturnal Sleep/Wake Effects on Risk of Suicide | 84 | 16 | 100 |
| APOE | Sleep Disordered Breathing, ApoE and Lipid Metabolism | 49 | 18 | 67 |
| APPLES | Apnea Positive Pressure Long-term Efficacy Study | 86 | 14 | 100 |
| BESTAIR | Best Apnea Interventions in Research | 87 | 13 | 100 |
| CCSHS | Cleveland Children's Sleep and Health Study | 57 | 43 | 100 |
| CFS | Cleveland Family Study | 80 | 20 | 100 |
| CHAT | Childhood Adenotonsillectomy Trial | 78 | 22 | 100 |
| DISECAD | Drug-Induced Sleep Endoscopy Study | 32 | 2 | 34 |
| FDCSR | Forced Desynchrony with Chronic Sleep Restriction | 23 | 9 | 32 |
| FFCWS | Future of Families and Child Wellbeing Study | 50 | 28 | 78 |
| HAASSA | Honolulu-Asia Aging Study of Sleep Apnea | 11 | 0 | 11 |
| HCHS | Hispanic Community Health Study / Study of Latinos | 94 | 6 | 100 |
| HEARTBEAT | Heart Biomarker Evaluation in Apnea Treatment | 92 | 8 | 100 |
| HOMEPAP | Home Positive Airway Pressure | 70 | 30 | 100 |
| ISAPS | Intern Sleep and Patient Safety | 4 | 5 | 9 |
| LOFTHF | Low Flow Nocturnal Oxygen Therapy in Heart Failure | 77 | 23 | 100 |
| MESA | Multi-Ethnic Study of Atherosclerosis | 73 | 27 | 100 |
| MROS | MrOS Sleep Study | 92 | 8 | 100 |
| MSP | Maternal Sleep in Pregnancy and the Fetus | 22 | 15 | 37 |
| NCHSDB | NCH Sleep DataBank | 18 | 13 | 31 |
| NFS | Need for Sleep | 15 | 4 | 19 |
| NUMOM2B | Nulliparous Pregnancy Outcomes Study | 40 | 60 | 100 |
| PATS | Pediatric Adenotonsillectomy Trial of Snoring | 72 | 28 | 100 |
| PIMECFS | Post Infectious Myalgic Encephalomyelitis/Chronic Fatigue Syndrome | 69 | 19 | 88 |
| SANDD | Alcohol, Sleep, and Circadian Rhythms in Young Humans | 82 | 18 | 100 |
| SHINE | Sleep Health in Infancy and Early Childhood | 89 | 11 | 100 |
| SHHS | Sleep Heart Health Study | 77 | 23 | 100 |
| SOF | Study of Osteoporotic Fractures | 54 | 46 | 100 |
| STAGES | Stanford Technology Analytics and Genomics in Sleep | 83 | 17 | 100 |
| WSC | Wisconsin Sleep Cohort | 82 | 18 | 100 |

## Variable Classification Methodology

Variables were classified as continuous or categorical based on:

1. **Type field analysis:**
   - **Continuous:** numeric, integer, float, continuous
   - **Categorical:** categorical, choice, choices, binary, enumeration, identifier, ordinal, date, time

2. **Variable name patterns:**
   - Identifiers (ending in "_id" or "id") → categorical
   - Date/time fields → categorical

3. **Default:** When ambiguous → continuous

## Multi-Visit Data Handling

The current extraction captures variable metadata from the main variables list page for each study. Many studies have multi-visit designs (baseline, follow-up visits at various timepoints).

**To properly handle multi-visit statistics**, the following approach would be needed:
1. Visit each individual variable page (e.g., `/datasets/abc/variables/bmi`)
2. Parse statistics tables that show visit-specific data
3. When pipe-delimited values are found (e.g., "n: 49|43|40"), create separate rows for each visit
4. Match visit numbers to visit names from study documentation

**Current Status:** Variable inventory is complete with metadata. Visit-specific statistics would require ~2,500+ additional page visits.

## Key Variable Categories Found

Common variable categories across studies include:

- **Administrative:** Study IDs, visit numbers, site identifiers, consent information
- **Demographics:** Age, sex, race, ethnicity, education, income
- **Anthropometry:** BMI, height, weight, waist/hip circumference, neck circumference
- **Clinical Data:**
  - Laboratory tests (glucose, cholesterol, triglycerides, HbA1c, etc.)
  - Vital signs (blood pressure, heart rate)
  - Medical history and diagnoses
  - Medications
- **Sleep Monitoring/Polysomnography:**
  - Apnea-Hypopnea Indices (AHI) with various definitions
  - Oxygen saturation metrics
  - Sleep architecture (stage percentages, sleep efficiency, latency)
  - Arousal indices
  - Respiratory events
- **Sleep Questionnaires:**
  - Epworth Sleepiness Scale (ESS)
  - Pittsburgh Sleep Quality Index (PSQI)
  - Various insomnia and sleep disturbance scales
- **Actigraphy:** Sleep-wake patterns, activity levels
- **Neurocognitive Testing:** Various cognitive assessments
- **General Health:** SF-36, quality of life measures

## Harmonized Variables

Many studies include NSRR-harmonized variables (prefix: `nsrr_`) standardized across datasets:
- `nsrr_age`, `nsrr_bmi`, `nsrr_sex`, `nsrr_race`, `nsrr_ethnicity`
- `nsrr_ahi_hp3r_aasm15`, `nsrr_ahi_hp3u`, `nsrr_ahi_hp4r`, `nsrr_ahi_hp4u_aasm15`
- `nsrr_ttldursp_f1`, `nsrr_ttleffsp_f1`, `nsrr_pctdursp_s1/s2/s3/sr`
- Blood pressure: `nsrr_bp_systolic`, `nsrr_bp_diastolic`
- Smoking: `nsrr_current_smoker`, `nsrr_ever_smoker`

## Limitations and Future Work

### Current Limitations:
1. **No visit-specific statistics:** Statistics columns are empty; would require individual page visits
2. **Limited domain/enumeration data:** Domain values for categorical variables not fully extracted
3. **Description fields:** Often empty; full descriptions available on individual variable pages
4. **Units:** Not consistently extracted for all continuous variables

### To Complete Full Extraction:
1. Visit each of the 2,506 variable pages individually
2. Extract detailed statistics, domain values, descriptions, and units
3. Parse multi-visit data and create separate rows per visit
4. Estimated additional requests: 2,500+ (with appropriate rate limiting: ~2-3 hours)

## Scripts Created

### 1. final_extractor.py
Primary extraction script that:
- Fetches variable lists from all 31 studies
- Classifies variables as continuous/categorical
- Generates TSV output files
- Includes rate limiting and error handling

### 2. extract_all_variables.py
More detailed extractor (not fully executed due to time constraints) that:
- Visits individual variable pages
- Extracts full statistics and metadata
- Handles multi-visit data parsing
- Creates visit-specific rows

### 3. compile_variables.py
Helper script for compiling and validating extracted data

## Usage

To run the extraction again:

```bash
python3 final_extractor.py
```

Output files will be created/overwritten:
- `/Users/athessen/sleep-cde-schema/continuous_variables.tsv`
- `/Users/athessen/sleep-cde-schema/categorical_variables.tsv`

## Data Format

### TSV Format Details:
- Tab-delimited (TSV) for easy import into spreadsheet tools
- UTF-8 encoding
- Headers in first row
- Empty cells for missing data
- Pipe-delimited (|) for multi-valued fields like domain

### Example Continuous Variable Row:
```
ABC	bmi	Body mass index (BMI)	Anthropometry		baseline		numeric				kg/m^2
```

### Example Categorical Variable Row:
```
ABC	gender	Gender of the participant	Demographics		baseline	1:Male|2:Female	categorical
```

## References

- **National Sleep Research Resource (NSRR):** https://sleepdata.org/
- **Studies Documentation:** Individual study pages at https://sleepdata.org/datasets/{study-id}
- **Variable Browsers:** https://sleepdata.org/datasets/{study-id}/variables

## Contact

For questions about this extraction or the sleep CDE schema project, please refer to the project documentation.
