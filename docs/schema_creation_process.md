# Sleep CDE Schema Creation Process

This document describes the steps used to create `sleep_cde_schema.yaml` from the NSRR (National Sleep Research Resource) variable data dictionaries.

## Source Data

The primary source is the NSRR variable data dictionary, available as tab-delimited (TSV) files from `sleepdata.org`. The data dictionaries cover 31 NSRR sleep studies and describe variables including their names, labels, types (continuous or categorical), domains (enumeration values), units, and per-visit summary statistics.

The authoritative list of variable names used as input was `catvcon.txt`, which lists every variable across all 31 studies with columns: `study_name`, `variable_name`, `type`, and `category`.

---

## Step 1: Project Initialization

A LinkML schema project was initialized using the LinkML project template (via `copier`). This created the standard project skeleton including `src/sleep_cde_schema/schema/sleep_cde_schema.yaml` as the target schema file, along with build tooling (`justfile`), documentation scaffolding (`mkdocs.yml`), and Python packaging configuration.

---

## Step 2: Initial Schema Generation from TSV (v1 — One Class per Variable)

**Script:** `generate_schema.py` (now in `variable_summary_attic/`)

A Python script was written to parse the NSRR data dictionary TSV and generate a LinkML schema where **each variable becomes a separate class**. Key features:

- Each row in the data dictionary produces one LinkML class, with `id` as the primary identifier.
- 16,261 classes were generated (11,077 unique variables plus 5,184 cross-study duplicates).
- 7 common slots were shared across all classes.
- 683 enumerations were created for categorical variables.
- Slot annotations included UCUM unit codes, formulas for calculated variables, and exact-match mappings to study/folder paths.

The resulting schema was ~274,000 lines of YAML.

Enumeration values for categorical variables (e.g., sex, race, treatment arm, smoking status) were subsequently updated to match the actual coded values from the NSRR datasets on `sleepdata.org`. Calculated variables (e.g., `omahi3`, `epepwort`) were given LinkML `formula` annotations. YAML syntax errors from this generation pass (unquoted `%` signs, boolean value collisions, numeric `is_a` fields) were also corrected.

---

## Step 3: Variable Metadata Extraction from sleepdata.org (Rounds 1–3)

Because the raw data dictionary TSV contains limited metadata (primarily variable names and types), richer metadata was scraped from the individual variable pages on `sleepdata.org`.

### Round 1 — Initial spreadsheet (12 studies, ~79 variables)

A tab-delimited summary spreadsheet (`sleep_variables_summary.tsv`) was created manually for 12 NSRR datasets (ABC, APPLES, BESTAIR, CHAT, CCSHS, CFS, HEARTBEAT, HCHS, HOMEPAP, MESA, MrOS, NUMOM2B), capturing:
- Variable identification (study, name, label)
- Classification (folder, domain, type)
- Summary statistics (n, mean, stddev, median, min, max)
- Multi-visit data using pipe (`|`) delimiters

### Round 2 — Continuous/categorical split (12–14 studies)

Variables were separated into two TSV files:
- `continuous_variables.tsv` — 166 variables with numeric measurements
- `categorical_variables.tsv` — 137 variables with discrete categories

A `studies_with_variables.txt` file was created listing all 31 NSRR datasets that had accessible variable data dictionaries.

### Round 3 — Full metadata extraction (31 studies, all 2,506 variables)

**Script:** `extract_variable_metadata.py` (now in `variable_summary_attic/`)

An automated scraping script fetched the individual variable page for each variable from:
```
https://sleepdata.org/datasets/{study}/variables/{variable_name}
```

The script used:
- Rate limiting (1.5 s/request) to avoid overloading the server
- Retry logic (up to 3 attempts per variable, 5 s delay)
- A URL case-sensitivity fix that was critical for correct page resolution

Results:
- **Continuous:** 1,920 input rows expanded to 3,224 rows by splitting multi-visit variables into separate per-visit rows; statistics (n, mean, stddev, median, min, max) populated per visit
- **Categorical:** 586 rows with domain enumerations in `code:label|code:label` pipe-delimited format
- Runtime: ~10.5 hours; 100% success rate (2,506/2,506 variables)

Output: `continuous_variables_updated.tsv`, `categorical_variables_updated.tsv`

### Round 3b — Missing variables and descriptions backfill

Additional scripts (`add_missing_variables.py`, `add_missing_visits.py`, `update_categorical_descriptions.py`) were used to:
- Add 413 previously missing continuous variables identified from `catvcon.txt`
- Add missing visit rows for all study/visit combinations
- Fetch descriptions for 593 categorical variables

Output: `continuous_variables_cde_updated.tsv` (4,154 rows, 1,480 unique variables), `categorical_variables_cde_updated.tsv` (1,028 rows, 1,027 unique variables)

These intermediate files and scripts were then moved to `variable_summary_attic/` to keep the working directory clean.

---

## Step 4: Schema Redesign — Compact CDE Model (v2)

**Commit:** "Redesign schema as compact CDE model with modifier axes"

The per-variable v1 schema (~235,000 lines) was replaced with a compact, reusable CDE model (~1,600 lines). The redesign followed cross-dataset harmonization principles:

### Core design principle — Category Collapse

If multiple variables represent the **same quantitative construct** but differ only by a categorical qualifier (e.g., body position, sleep stage, event subtype, oxygen threshold), one canonical slot is created for the quantitative construct and **modifier axis enum slots** represent the categorical dimension. Examples:

| Old approach | New approach |
|---|---|
| `supine_duration_min`, `lateral_duration_min` | `body_position_duration_min` + `body_position` modifier |
| `central_apnea_index`, `obstructive_apnea_index` | `apnea_index` + `apnea_type` modifier |
| `odi3`, `odi4`, `odi5` | `desaturation_index` + `desaturation_threshold` modifier |
| `time_below_90_pct_min` | `time_below_spo2_threshold_min` + `spo2_threshold` modifier |
| `respiratory_arousal_index`, `spontaneous_arousal_index` | `arousal_index` + `arousal_type` modifier |

### Schema structure

- **30 concept groups** (Demographics, Sleep Architecture, Respiratory Events, Oxygen Saturation, Arousals, Limb Movements, Body Position, HRV, Questionnaires, Medical History, Labs, Actigraphy, CPAP, Snoring, CO2/Capnography, Neurobehavioral Performance, Pediatric, Screening Questionnaires, PROMIS, etc.)
- **134+ canonical measurement slots**
- **9 modifier axis enums** (`SleepStageEnum`, `BodyPositionEnum`, `PSGTypeEnum`, `ApneaTypeEnum`, `HypopneaDefinitionEnum`, `DesaturationThresholdEnum`, `ArousalRequirementEnum`, `SummaryStatisticEnum`, `TimeFrameEnum`)
- **22+ total enums** including value sets
- **24 classes** for data storage and mapping, including a `SurveyItemResponse` class for questionnaire items and a `Variable` class for dataset-local fallback mappings

A companion document `docs/cde_mapping_guide.md` was added describing the concept groups, modifier axes, canonical slot inventory, and 10 example variable-to-CDE mappings.

---

## Step 5: Complete Variable Extraction (All 31 Studies, Full Pagination)

**Script:** `extract_all_study_variables.py`

The earlier extractions were limited to 100 variables per study due to pagination. A new extraction script was written to:
- Fetch all pages of variables per study from `sleepdata.org`
- Compare against the existing TSV files and add missing variables
- Handle rate limiting (1.0 s/request) and retries
- Track progress in `extraction_progress.json` for resumability

Results after this round:
- **Continuous:** 59,487 rows
- **Categorical:** 7,230 rows
- **Total:** 66,717 rows across all 31 studies

Six new concept groups were added to the schema based on variables discovered in this pass:
- Snoring metrics (duration, loudness, frequency)
- CO2/capnography measures (etCO2, time above thresholds)
- Neurobehavioral performance (PVT, KSS)
- Pediatric-specific measures (CHQ, OSA-18, tonsil size)
- Sleep apnea screening questionnaires (Berlin, STOP-BANG)
- PROMIS sleep measures

---

## Step 6: Ontology Annotation of TSV Files

Ontology CURIEs and semantic class labels were added to the TSV files as additional columns to support downstream harmonization.

### 6a — CURIE column (OBA and OMOP)

**Script:** `add_curie_column_fast.py`

A `CURIE` column was inserted between `variable_label` and `folder`. Mapping strategy:
1. Search **OBA** (Ontology of Biological Attributes) via the EBI OLS4 API for biological/physical measurements (anthropometry, vitals, labs)
2. Fall back to **OMOP** (via BioPortal API) for clinical concepts (sleep indices, questionnaire scores, medical conditions)
3. Apply an extensive keyword mapping table for common sleep and clinical terms
4. Cache API results to `curie_mapping_cache.json` to avoid redundant requests

Coverage: ~6.8% of continuous variables (4,018/59,487) and ~11% of categorical variables (795/7,230).

### 6b — BDCHM class column

**Script:** `add_bdchm_class.py`

A `bdchm_class` column was inserted between `variable_label` and `CURIE`. Variables were classified according to the **BioData Catalyst Harmonized Model (BDCHM)** from RTI International/NHLBI-BDC-DMC-HM. Classes assigned include:

| BDCHM Class | Count (continuous) | Examples |
|---|---|---|
| `MeasurementObservation` | 13,253 | Labs, vitals, PSG metrics |
| `QuestionnaireResponse` | 712 | ESS, PSQI, PHQ-9 |
| `Demography` | 582 | Age, sex, race, ethnicity |
| `Visit` | 387 | Study timepoints |
| `Condition` | 495 | Diagnoses, medical history |
| `Exposure` | 169 | Smoking, alcohol |
| `DrugExposure` | 153 | Medications |
| `DeviceExposure` | 47 | CPAP, PAP devices |
| `Procedure` | 64 | Surgeries, titrations |
| `SdohObservation` | 40 | Social determinants |

Coverage: 24.2% of continuous rows (14,425/59,487) and 21.5% of categorical rows (1,552/7,230).

### 6c — Disease and drug CURIEs (Mondo/HPO and RxNorm)

**Script:** `update_condition_drug_curies.py`

Rows classified as `Condition` were mapped to **Mondo Disease Ontology** CURIEs (e.g., `MONDO:0005296` for sleep apnea, `MONDO:0005044` for hypertension) with fallback to **HPO** for phenotypic features. Rows classified as `DrugExposure` were mapped to **RxNorm** CURIEs (e.g., `RxNorm:5856` for insulin, `RxNorm:1191` for aspirin).

Coverage: 93% of Condition rows (461/495) and 93% of DrugExposure rows (143/153).

---

## Step 7: Category Collapse Refactoring of Schema

Two final refactoring commits applied the category collapse design principle consistently across remaining schema slots:

**Commit 1:** "Refactor schema: collapse category-specific slots into canonical slots with modifiers"
- Added `SpO2ThresholdEnum` and `CO2ThresholdEnum` modifier axes
- Replaced body position slots (`supine_duration_min`, etc.) with `body_position_duration_min` + `body_position` modifier
- Replaced apnea type slots with `apnea_index` + `apnea_type` modifier
- Replaced SpO2 threshold slots with `time_below_spo2_threshold_min` + `spo2_threshold` modifier
- Replaced CO2 threshold slots with `time_above_co2_threshold_percent` + `co2_threshold` modifier

**Commit 2:** "Collapse arousal type-specific slots into canonical arousal_index with modifier"
- Added `ArousalTypeEnum` (values: `all`, `respiratory`, `spontaneous`, `plm`)
- Added `arousal_type` modifier slot
- Removed separate `respiratory_arousal_index`, `spontaneous_arousal_index`, `plm_arousal_index` slots
- Updated `ArousalMetric` class to use the modifier pattern

---

## Output Files

| File | Description |
|---|---|
| `src/sleep_cde_schema/schema/sleep_cde_schema.yaml` | Final LinkML schema (v2, ~2,100 lines) |
| `continuous_variables_cde_updated.tsv` | 59,487 rows; continuous variables with metadata, CURIEs, BDCHM classes |
| `categorical_variables_cde_updated.tsv` | 7,230 rows; categorical variables with metadata, CURIEs, BDCHM classes |
| `docs/cde_mapping_guide.md` | Mapping guide: concept groups, modifier axes, example mappings |
| `variable_summary_attic/` | Intermediate files and extraction scripts archived for reproducibility |

---

## Key Design Decisions

1. **Compact CDE model over per-variable enumeration.** The v1 approach of one class per variable (16,000+ classes) was unworkable for cross-study harmonization. The v2 model uses ~134 canonical slots organized into 30 concept groups.

2. **Modifier axes over concatenated variable names.** Rather than creating separate slots for every combination of measurement × qualifier, modifier enums capture the categorical dimension while keeping the quantitative construct as a single canonical slot.

3. **Mapping priority.** Variables are mapped to CDEs in this order: NSRR harmonized variable tags > concept tags > compositional tag parsing > concept path matching > dataset-local fallback via the `Variable` class.

4. **TSV as the working data format.** The enriched TSV files serve as an intermediate representation between the raw NSRR data dictionaries and the LinkML schema, allowing iterative enrichment (adding CURIEs, BDCHM classes, statistics) without re-parsing the schema each time.
