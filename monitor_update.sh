#!/bin/bash
# Monitor update progress

echo "=== UPDATE PROGRESS MONITOR ==="
echo ""
echo "Started: $(date)"
echo ""

# Find the Python process
PID=$(pgrep -f "python3 update_curated_files.py")
if [ -z "$PID" ]; then
    echo "❌ Update process not running"
    exit 1
fi

echo "✅ Process running (PID: $PID)"
echo ""

# Check output files
if [ -f "/Users/athessen/sleep-cde-schema/continuous_variables_updated_curated_final.tsv" ]; then
    CONT_ROWS=$(wc -l < /Users/athessen/sleep-cde-schema/continuous_variables_updated_curated_final.tsv)
    echo "📁 Continuous output: $CONT_ROWS rows"
fi

if [ -f "/Users/athessen/sleep-cde-schema/categorical_variables_updated_curated_final.tsv" ]; then
    CAT_ROWS=$(wc -l < /Users/athessen/sleep-cde-schema/categorical_variables_updated_curated_final.tsv)
    echo "📁 Categorical output: $CAT_ROWS rows"
fi

echo ""
echo "Expected completion times:"
echo "  Continuous: ~26 minutes (1,068 unique variables)"
echo "  Categorical: ~26 minutes (1,025 variables)"
echo "  Total: ~52 minutes"
echo ""
