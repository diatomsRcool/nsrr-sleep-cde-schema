# Sleep CDE Mapping Guide

This document describes the canonical Common Data Element (CDE) model for sleep research, including concept groups, mapping strategies, and example mappings.

## A) Concept Groups (24 groups)

The schema organizes sleep research variables into 24 hierarchical concept groups derived from sleepdata.org folder structures:

| # | Concept Group | Description | Key Canonical Slots |
|---|---------------|-------------|---------------------|
| 1 | Demographics & Socioeconomic | Subject demographic information | `age_years`, `sex`, `ethnicity`, `race`, `education_years` |
| 2 | Anthropometry | Physical body measurements | `height_cm`, `weight_kg`, `bmi`, `neck_circumference_cm` |
| 3 | Vital Signs | Blood pressure, heart rate, etc. | `systolic_bp_mmhg`, `diastolic_bp_mmhg`, `heart_rate_bpm` |
| 4 | Sleep Architecture | Staging, efficiency, latency | `total_sleep_time_min`, `sleep_efficiency_pct`, `sleep_onset_latency_min`, `waso_min` |
| 5 | Sleep Timing & Circadian | Bedtime, wake time, midpoint | `lights_off_time`, `lights_on_time`, `sleep_midpoint` |
| 6 | Respiratory Events - Apneas | Apnea indices and counts | `apnea_index`, `apnea_count`, `mean_apnea_duration_sec` |
| 7 | Respiratory Events - Hypopneas | Hypopnea indices and counts | `hypopnea_index`, `hypopnea_count` |
| 8 | Respiratory Events - Combined | AHI, RDI | `ahi`, `rdi`, `rera_index` |
| 9 | Oxygen Saturation | SpO2 metrics | `spo2_mean_pct`, `spo2_min_pct`, `desaturation_index`, `time_below_90_pct_min` |
| 10 | Arousals | Arousal indices | `arousal_index`, `respiratory_arousal_index`, `spontaneous_arousal_index` |
| 11 | Limb Movements | PLM indices | `plm_index`, `plms_with_arousal_index` |
| 12 | Body Position | Position during sleep | `supine_percent`, `non_supine_percent` |
| 13 | Heart Rate Variability | HRV metrics | `hrv_sdnn_ms`, `hrv_rmssd_ms`, `hrv_lf_hf_ratio` |
| 14 | Signal Quality | Recording quality metrics | `eeg_quality_pct`, `oximetry_quality_pct`, `overall_study_quality` |
| 15 | Questionnaires - Sleepiness | ESS and similar | `ess_total_score` + `SurveyItemResponse` |
| 16 | Questionnaires - Sleep Quality | PSQI | `psqi_global_score` + `SurveyItemResponse` |
| 17 | Questionnaires - Insomnia | ISI, WHIIRS | `isi_total_score` + `SurveyItemResponse` |
| 18 | Questionnaires - Chronotype | MEQ | `meq_score`, `chronotype` |
| 19 | General Health Questionnaires | Depression, anxiety, QoL | `phq9_total_score`, `gad7_total_score`, `cesd_total_score`, `sf36_physical_score` |
| 20 | Medical History | Comorbidities | `has_hypertension`, `has_diabetes`, `has_heart_disease` |
| 21 | Laboratory Tests | Blood tests, biomarkers | (dataset-local variables mapped via `Variable` class) |
| 22 | Actigraphy | Actigraphy-derived sleep | `actigraphy_tst_min`, `actigraphy_se_pct`, `actigraphy_waso_min` |
| 23 | Treatment Adherence | CPAP usage | `cpap_usage_hours`, `cpap_ahi_residual` |
| 24 | Administrative | Study metadata | (via `Dataset` and `Variable` classes) |

## B) Canonical CDE Inventory

### Modifier Axes

The schema separates measurement semantics from acquisition/scoring protocol using these modifier axes:

| Modifier Axis | Enum | Values | Purpose |
|---------------|------|--------|---------|
| Sleep Stage | `SleepStageEnum` | `all_sleep`, `wake`, `nrem`, `n1`, `n2`, `n3`, `rem` | Stratify by sleep stage |
| Body Position | `BodyPositionEnum` | `all_positions`, `supine`, `non_supine`, `lateral`, `prone` | Stratify by position |
| PSG Type | `PSGTypeEnum` | `type_i`, `type_ii`, `type_iii`, `type_iv`, `actigraphy` | Recording type |
| Apnea Type | `ApneaTypeEnum` | `all`, `obstructive`, `central`, `mixed` | Filter apnea events |
| Hypopnea Definition | `HypopneaDefinitionEnum` | `aasm_2015_1a`, `aasm_2015_1b`, `chicago_1999`, etc. | Scoring rule |
| Desaturation Threshold | `DesaturationThresholdEnum` | `none`, `desat_3pct`, `desat_4pct` | Event threshold |
| Arousal Requirement | `ArousalRequirementEnum` | `with_or_without`, `required`, `or_arousal` | Event criterion |
| Summary Statistic | `SummaryStatisticEnum` | `mean`, `min`, `max`, `count`, `index`, `percent` | Aggregation type |
| Time Frame | `TimeFrameEnum` | `full_night`, `weekday`, `weekend`, `past_month` | Temporal scope |

### Canonical Slot Counts by Group

| Concept Group | # Canonical Slots | Example Slots |
|---------------|-------------------|---------------|
| Identifiers | 5 | `id`, `subject_id`, `visit_id`, `dataset_id`, `variable_id` |
| Demographics | 10 | `age_years`, `sex`, `ethnicity`, `race`, `education_years` |
| Anthropometry | 9 | `height_cm`, `weight_kg`, `bmi`, `neck_circumference_cm` |
| Vital Signs | 5 | `systolic_bp_mmhg`, `diastolic_bp_mmhg`, `heart_rate_bpm` |
| Sleep Architecture | 10 | `total_sleep_time_min`, `sleep_efficiency_pct`, `sleep_stage_percent` |
| Sleep Timing | 7 | `lights_off_time`, `sleep_onset_time`, `sleep_midpoint` |
| Respiratory Events | 12 | `ahi`, `apnea_index`, `hypopnea_index`, `apnea_count` |
| Oxygen Saturation | 9 | `spo2_mean_pct`, `spo2_min_pct`, `desaturation_index` |
| Arousals | 6 | `arousal_index`, `respiratory_arousal_index` |
| Limb Movements | 5 | `plm_index`, `plms_with_arousal_index` |
| Body Position | 6 | `supine_percent`, `non_supine_percent` |
| Heart Rate/HRV | 9 | `mean_heart_rate_sleep`, `hrv_sdnn_ms`, `hrv_rmssd_ms` |
| Signal Quality | 8 | `eeg_quality_pct`, `oximetry_quality_pct` |
| Questionnaire Scores | 14 | `ess_total_score`, `psqi_global_score`, `phq9_total_score` |
| Survey Items | 5 | `instrument_id`, `item_id`, `response_value` |
| Actigraphy | 8 | `actigraphy_tst_min`, `actigraphy_se_pct` |
| CPAP Adherence | 6 | `cpap_usage_hours`, `cpap_ahi_residual` |
| Medical History | 11 | `has_hypertension`, `has_diabetes`, `smoking_status` |
| Mapping/Metadata | 9 | `canonical_slot`, `modifiers`, `mapping_confidence` |
| **TOTAL** | **~115 slots** | |

## C) Mapping Strategy

### Priority Order for Variable Mapping

1. **Exact NSRR Harmonized Match** (confidence: `exact`)
   - Variables prefixed with `nsrr_` map directly to canonical slots
   - Example: `nsrr_ahi_hp3u` → `ahi` with modifiers

2. **Concept Tag Match** (confidence: `high`)
   - Match concept tags from variable metadata to canonical concepts
   - Example: tag `subjective_sleepiness` → `ess_total_score`

3. **Instrument Item Tag via SurveyItemResponse** (confidence: `exact`)
   - Questionnaire items map to `SurveyItemResponse` class
   - Example: `ess_01sit` → `SurveyItemResponse(instrument_id="ESS", item_id="01")`

4. **Compositional Tag Parsing** (confidence: `high`)
   - Parse structured tags into canonical slot + modifiers
   - Example: `ahi_ap0uhp3x3r_f1t1` → parsed components

5. **Concept Path + Label Similarity** (confidence: `medium`)
   - Match based on folder hierarchy and label text
   - Example: folder `Sleep Monitoring/Polysomnography/Apnea-Hypopnea Indices` → respiratory event slots

6. **Dataset-Local Fallback** (confidence: `low`)
   - Variables not matching above are stored as `dataset_local` with metadata preserved
   - Mapped via `Variable` class with `canonical_slot=null`

### Compositional Tag Parsing Rules

The NSRR uses structured variable names that encode measurement parameters. Parse these as follows:

#### AHI Variable Pattern: `{measure}_{apnea_def}{hypopnea_def}_{psg_type}`

| Component | Pattern | Example | Maps To |
|-----------|---------|---------|---------|
| Measure | `ahi`, `oahi`, `cahi`, `ai`, `hi` | `ahi` | `ahi` slot + `apnea_type` modifier |
| Apnea Def | `ap{desat}{arousal}` | `ap0u` = no desat, with/without arousal | `desaturation_threshold`, `arousal_requirement` |
| Hypopnea Def | `hp{flow}x{desat}{arousal}` | `hp3x3r` = 30% flow, 3% desat OR arousal | `hypopnea_definition` |
| PSG Type | `f{type}t{subtype}` | `f1t1` = type I PSG | `psg_type` |

#### Sleep Stage Suffixes

| Suffix | Sleep Stage |
|--------|-------------|
| `_sn` | NREM sleep |
| `_sr` | REM sleep |
| `_s1` | Stage N1 |
| `_s2` | Stage N2 |
| `_s3` | Stage N3 |

#### Body Position Suffixes

| Suffix | Body Position |
|--------|---------------|
| `_pb` | Supine |
| `_po` | Non-supine |

### Survey Instrument Mapping

Questionnaire items should be mapped to the `SurveyItemResponse` class rather than creating individual slots:

```yaml
# Example: ESS item mapping
source_variable: ess_01sit
maps_to:
  class: SurveyItemResponse
  instrument_id: "ESS"
  item_id: "01"
  item_text: "Sitting and reading"
```

Standard instruments recognized:
- **ESS** - Epworth Sleepiness Scale (8 items, score 0-24)
- **PSQI** - Pittsburgh Sleep Quality Index (19 items, score 0-21)
- **PHQ-9** - Patient Health Questionnaire (9 items, score 0-27)
- **GAD-7** - Generalized Anxiety Disorder (7 items, score 0-21)
- **CES-D** - Center for Epidemiologic Studies Depression (20 items)
- **ISI** - Insomnia Severity Index (7 items, score 0-28)
- **FSS** - Fatigue Severity Scale (9 items)
- **MEQ** - Morningness-Eveningness Questionnaire

## D) Example Mappings (10 examples)

### 1. NSRR Harmonized AHI (exact match)
```yaml
source:
  dataset: SHHS
  variable: nsrr_ahi_hp3u
  label: "Apnea-Hypopnea Index : (All apneas + hypopneas with >= 3% oxygen desaturation) / hour of sleep"
  concept_path: "Harmonized/Polysomnography/Apnea-Hypopnea Indices"
mapping:
  canonical_slot: ahi
  modifiers:
    - apnea_type: all
    - hypopnea_definition: desat_3_only
    - desaturation_threshold: desat_3pct
    - arousal_requirement: with_or_without
    - sleep_stage: all_sleep
    - body_position: all_positions
  confidence: exact
```

### 2. Compositional AHI Tag (parsed)
```yaml
source:
  dataset: CFS
  variable: ahi_ap0uhp3x3r_f1t1
  label: "Apnea-Hypopnea Index: (All apneas with no oxygen desaturation threshold used and with or without arousal + hypopneas with > 30% flow reduction and with >= 3% oxygen desaturation or with arousal) / hour of sleep from type I polysomnography"
mapping:
  canonical_slot: ahi
  modifiers:
    - apnea_type: all
    - hypopnea_definition: aasm_2015_1a
    - desaturation_threshold: desat_3pct
    - arousal_requirement: or_arousal
    - psg_type: type_i
  confidence: high
  notes: "Parsed from compositional tag"
```

### 3. Obstructive AHI by Position
```yaml
source:
  dataset: MESA
  variable: nsrr_oahi_hp3u_pb
  label: "Obstructive Apnea-Hypopnea Index for supine sleep"
mapping:
  canonical_slot: ahi
  modifiers:
    - apnea_type: obstructive
    - hypopnea_definition: desat_3_only
    - body_position: supine
  confidence: exact
```

### 4. Sleep Stage Percentage
```yaml
source:
  dataset: SHHS
  variable: nsrr_pctdursp_sr
  label: "Percentage of total sleep duration (i.e., total sleep time, TST) in REM from polysomnography"
mapping:
  canonical_slot: sleep_stage_percent
  modifiers:
    - sleep_stage: rem
  confidence: exact
```

### 5. Oxygen Saturation Mean
```yaml
source:
  dataset: CFS
  variable: avglvlsa_f1t1
  label: "Average oxygen saturation level in total sleep duration from type I polysomnography"
mapping:
  canonical_slot: spo2_mean_pct
  modifiers:
    - summary_statistic: mean
    - sleep_stage: all_sleep
    - psg_type: type_i
  confidence: high
```

### 6. PSQI Component Score
```yaml
source:
  dataset: HCHS
  variable: sleep_quality
  label: "Pittsburgh Sleep Quality Index: Rate overall sleep quality last month"
  concept_path: "Sleep Questionnaires/General and Sleep Disorder Screening/Pittsburgh Sleep Quality Index (PSQI)"
mapping:
  canonical_slot: null
  class: SurveyItemResponse
  instrument_id: PSQI
  item_id: "component_1"
  confidence: high
  notes: "Maps to PSQI Component 1 (Subjective sleep quality)"
```

### 7. CES-D Item Response
```yaml
source:
  dataset: MESA
  variable: cesd_6
  label: "Center for Epidemiologic Studies Depression Scale: Over the past 2 weeks, I felt depressed."
mapping:
  canonical_slot: null
  class: SurveyItemResponse
  instrument_id: CES-D
  item_id: "6"
  confidence: exact
```

### 8. PLM Index
```yaml
source:
  dataset: MROS
  variable: plmindex
  label: "Periodic limb movement index - Number of periodic limb movement per hour of sleep from type I polysomnography"
mapping:
  canonical_slot: plm_index
  modifiers:
    - sleep_stage: all_sleep
    - psg_type: type_i
  confidence: high
```

### 9. Body Position Duration
```yaml
source:
  dataset: SHHS
  variable: supinep
  label: "Percentage duration of sleep in supine position from type I polysomnography"
mapping:
  canonical_slot: supine_percent
  modifiers:
    - psg_type: type_i
  confidence: exact
```

### 10. Dataset-Local Variable (laboratory test)
```yaml
source:
  dataset: ABC
  variable: active_ghrelin
  label: "Active Ghrelin"
  concept_path: "Clinical Data/Laboratory Tests"
  units: "pg/mL"
mapping:
  canonical_slot: null
  class: Variable
  confidence: dataset_local
  notes: "Laboratory biomarker not in canonical CDE set; preserved as dataset-local variable"
```

## E) Implementation Notes

### Using the Schema for Cross-Dataset Mapping

1. **Load source variables** from dataset metadata (TSV files)
2. **Apply mapping rules** in priority order
3. **Generate `VariableMapping` instances** for each source variable
4. **Transform data** using canonical slots and modifiers
5. **Store harmonized data** in appropriate measurement classes

### Key Classes for Data Storage

| Class | Use Case |
|-------|----------|
| `RespiratoryEventMetric` | AHI, apnea/hypopnea indices with full modifier context |
| `OxygenSaturationMetric` | SpO2 measurements with modifiers |
| `SleepStageMetric` | Stage-stratified duration/percentage |
| `SleepStudyRecord` | Complete PSG summary for a subject-visit |
| `SurveyItemResponse` | Individual questionnaire item responses |
| `SurveyScore` | Computed questionnaire scores |
| `Variable` | Dataset-local variables not mapped to canonical CDEs |
| `VariableMapping` | Documentation of source→canonical mappings |

### Quality Checks

Before finalizing mappings:
- Verify total canonical slots < 200 (target: 40-120)
- Check no slot name has >5 concatenated components
- Confirm questionnaire items use `SurveyItemResponse`, not individual slots
- Validate modifier combinations are clinically meaningful
