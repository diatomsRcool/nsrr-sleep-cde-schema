#!/bin/bash
# Monitor extraction progress

echo "=== Extraction Progress ==="
echo ""

# Check if process is running
if pgrep -f "extract_all_study_variables.py" > /dev/null; then
    echo "Status: RUNNING"
else
    echo "Status: NOT RUNNING (may have completed or stopped)"
fi

echo ""
echo "=== Latest log entries ==="
tail -20 /Users/athessen/sleep-cde-schema/full_extraction_log.txt

echo ""
echo "=== Current TSV counts ==="
echo "Continuous: $(wc -l < continuous_variables_cde_updated.tsv) rows"
echo "Categorical: $(wc -l < categorical_variables_cde_updated.tsv) rows"

echo ""
echo "=== Progress file ==="
if [ -f extraction_progress.json ]; then
    cat extraction_progress.json
fi
