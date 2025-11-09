#!/bin/bash

# Batch processing script for lines2.txt OCR synthesis
# Usage: ./run_single_batch2.sh <start_line> <end_line> <orientation>
# Example: ./run_single_batch2.sh 0 5000 h

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <start_line> <end_line> <orientation>"
    echo "Example: $0 0 5000 h"
    echo "  orientation: h (horizontal) or v (vertical)"
    exit 1
fi

START=$1
END=$2
ORIENT=$3

if [ "$ORIENT" != "h" ] && [ "$ORIENT" != "v" ]; then
    echo "Error: orientation must be 'h' or 'v'"
    exit 1
fi

# Set output directory based on orientation
if [ "$ORIENT" = "h" ]; then
    OUTDIR="out2_h_${START}_${END}"
    ORIENT_FLAG=""
else
    OUTDIR="out2_v_${START}_${END}"
    ORIENT_FLAG="--vertical"
fi

echo "=========================================="
echo "Batch OCR Synthesis - Lines2.txt"
echo "=========================================="
echo "Lines: $START to $END"
echo "Orientation: $([ "$ORIENT" = "h" ] && echo "Horizontal" || echo "Vertical")"
echo "Output: $OUTDIR"
echo "=========================================="

# Run synthesis
python3 synth.py \
    --lines lines2.txt \
    --out_dir "$OUTDIR" \
    --start_line "$START" \
    --end_line "$END" \
    --n_per_line 5 \
    --num_workers 8 \
    $ORIENT_FLAG

echo ""
echo "=========================================="
echo "Batch completed: $OUTDIR"
echo "=========================================="
