#!/bin/bash
# Wait for extraction to complete and monitor progress

LOG_FILE="/Users/athessen/sleep-cde-schema/extraction_log.txt"

echo "Monitoring extraction process..."
echo "Will check status at key milestones"
echo ""

# Monitor at 400, 600, 800, 1000, 1200, 1400, 1600, 1800 variables
for milestone in 400 600 800 1000 1200 1400 1600 1800; do
    echo "Waiting for milestone: $milestone variables..."

    while true; do
        if grep -q "Progress: $milestone/1920" "$LOG_FILE" 2>/dev/null; then
            echo ""
            echo "=== Reached $milestone/1920 variables ==="
            python3 /Users/athessen/sleep-cde-schema/extraction_status.py | head -15
            echo ""
            break
        fi
        sleep 60
    done
done

echo ""
echo "Nearly complete! Waiting for final processing..."
echo ""

# Wait for completion
while true; do
    if grep -q "Continuous variables complete" "$LOG_FILE" 2>/dev/null; then
        echo "=== CONTINUOUS VARIABLES COMPLETE ==="
        echo ""
        break
    fi
    sleep 30
done

# Wait for categorical to complete
while true; do
    if grep -q "Categorical variables complete" "$LOG_FILE" 2>/dev/null; then
        echo "=== CATEGORICAL VARIABLES COMPLETE ==="
        echo ""
        break
    fi
    sleep 30
done

echo "=== EXTRACTION COMPLETE ==="
python3 /Users/athessen/sleep-cde-schema/extraction_status.py
