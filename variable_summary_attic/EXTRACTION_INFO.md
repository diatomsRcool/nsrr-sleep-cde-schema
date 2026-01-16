# NSRR Variable Metadata Extraction - Process Information

## Overview
Comprehensive extraction of metadata from 2,506 NSRR sleep study variables across 31 studies.

## Status: IN PROGRESS
- **Started**: 2026-01-09 16:06:52
- **Estimated completion**: 18:14-18:26 (approximately 2 hours from start)
- **Current rate**: ~13-15 variables/minute

## Files Being Processed

### Input Files:
1. **Continuous variables**: `/Users/athessen/sleep-cde-schema/continuous_variables.tsv` (1,920 variables)
2. **Categorical variables**: `/Users/athessen/sleep-cde-schema/categorical_variables.tsv` (586 variables)

### Output Files (created upon completion):
1. **Continuous updated**: `/Users/athessen/sleep-cde-schema/continuous_variables_updated.tsv`
2. **Categorical updated**: `/Users/athessen/sleep-cde-schema/categorical_variables_updated.tsv`

### Log Files:
1. **Main log**: `/Users/athessen/sleep-cde-schema/extraction_log.txt`
2. **Error log**: `/Users/athessen/sleep-cde-schema/extraction_errors.txt`

## What's Being Extracted

### For Continuous Variables:
- **Description**: Full variable description from individual page
- **Type**: Precise type (Numeric, Integer, Float, etc.)
- **Units**: Units of measurement (kg, cm, kg/m², mmHg, events/h, %, etc.)
- **Visit-level statistics** (one row per visit):
  - n (sample size)
  - mean
  - stddev (standard deviation)
  - median
  - min (minimum)
  - max (maximum)
  - unknown (missing values)
  - visit name (Baseline, 9-Month Followup, etc.)

### For Categorical Variables:
- **Description**: Full variable description
- **Type**: Precise type (Categorical, Choices, Enumeration, etc.)
- **Domain**: All possible values in pipe-delimited format
  - Format: `code:label|code:label|...`
  - Examples:
    - `1:Male|2:Female`
    - `1:White|2:Black or African American|3:Asian|4:Other`
    - `0:No|1:Yes`

## Process Details

### Rate Limiting:
- **Delay between requests**: 1.5 seconds
- **Purpose**: Avoid overloading sleepdata.org servers
- **Timeout per request**: 30 seconds
- **Max retries**: 3 attempts per variable

### Visit Data Handling:
- Variables with multiple visits are expanded into separate rows
- Only true visit data is included (not demographic breakdowns)
- Visit names preserved exactly as shown on source pages

### Error Handling:
- Failed requests are retried up to 3 times
- All errors logged to `extraction_errors.txt`
- Original data preserved if extraction fails
- Process continues even if individual variables fail

## Monitoring the Process

### Quick Status Check:
```bash
python3 /Users/athessen/sleep-cde-schema/extraction_status.py
```

### View Latest Progress:
```bash
tail -20 /Users/athessen/sleep-cde-schema/extraction_log.txt
```

### Check for Errors:
```bash
tail /Users/athessen/sleep-cde-schema/extraction_errors.txt
```

### Monitor Script:
```bash
/Users/athessen/sleep-cde-schema/monitor_extraction.sh
```

## Expected Results

### Continuous Variables:
- **Input rows**: 1,920
- **Output rows**: Potentially 3,000+ (with visit expansion)
- **New columns populated**: description, type, units, visit, n, mean, stddev, median, min, max, unknown

### Categorical Variables:
- **Input rows**: 586
- **Output rows**: 586 (no expansion)
- **New columns populated**: description, type, domain (with all enumeration values)

## Completion Steps

Once extraction completes:

1. **Validate output files**:
   - Check row counts
   - Verify data quality
   - Review error log

2. **Replace original files** (after validation):
   ```bash
   mv continuous_variables_updated.tsv continuous_variables.tsv
   mv categorical_variables_updated.tsv categorical_variables.tsv
   ```

3. **Review extraction summary** in log file

## Technical Details

### Parser Capabilities:
- Extracts metadata from HTML form groups
- Parses statistics tables with visit rows
- Extracts domain values from bullet lists and tables
- Handles multiple table formats
- Filters out demographic breakdowns
- Cleans and normalizes text

### Source URLs:
Variables are fetched from:
```
https://sleepdata.org/datasets/{study}/variables/{variable_name}
```

### Studies Included:
31 NSRR sleep studies including: ABC, ANSWERS, APOE, BESTAIR, CHAT, CFS, CCSHS, HAASSA, HEARTBEAT, HCHS, HOMEPAP, LEARN, MESA, MrOS, NSRR-NSF, NCHSDB, NUMOM2B, PHSS, SHHS, SOF, WSC, and others.

## Notes

- **Data validation**: All numeric fields cleaned (removed non-numeric characters)
- **Text cleaning**: HTML removed, whitespace normalized
- **Units preserved**: Exact units as shown on source pages
- **Domain format**: Standardized pipe-delimited format for categorical values
- **Multi-visit variables**: Expanded only for true temporal visits, not demographic groups

## Estimated Timeline

Based on current performance:
- **Continuous variables**: ~2 hours (1,920 variables)
- **Categorical variables**: ~1 hour (586 variables)
- **Total estimated time**: ~3 hours

The process is designed to be robust and will complete successfully even if some individual variable pages fail to load.
