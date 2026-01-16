#!/bin/bash
# Monitor the extraction process

LOG_FILE="/Users/athessen/sleep-cde-schema/extraction_log.txt"
ERROR_FILE="/Users/athessen/sleep-cde-schema/extraction_errors.txt"

echo "=== Extraction Progress Monitor ==="
echo ""

# Get total lines in log
total_lines=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "0")
echo "Log entries: $total_lines"

# Get latest progress
echo ""
echo "Latest progress:"
grep "Processing " "$LOG_FILE" | tail -5

# Get progress updates
echo ""
echo "Progress updates:"
grep "Progress:" "$LOG_FILE" | tail -3

# Check for errors
error_count=$(wc -l < "$ERROR_FILE" 2>/dev/null || echo "0")
echo ""
echo "Errors logged: $error_count"
if [ "$error_count" -gt 0 ]; then
    echo "Recent errors:"
    tail -5 "$ERROR_FILE"
fi

# Check output files
echo ""
echo "Output files:"
ls -lh /Users/athessen/sleep-cde-schema/*_updated.tsv 2>/dev/null || echo "No output files yet"

echo ""
echo "=== End of Monitor ==="
