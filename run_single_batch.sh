#!/bin/bash
# Single batch runner - for manual execution to avoid CPU timeout
# Usage: ./run_single_batch.sh <start_line> <end_line> [orientation]
#   orientation: h (horizontal, default) or v (vertical)

set -euo pipefail

# ============================================================
# Configuration
# ============================================================
LINES_FILE="lines.txt"
FONTS_DIR="fonts"
BGS_DIR="backgrounds"
OUT_DIR_H="/mnt/whliao/ocr_out_h"
OUT_DIR_V="/mnt/whliao/ocr_out_v"

N_PER_LINE=20
BOX_JITTER="2,2"
LAST_RESORT_FONT="NotoSansTC-Regular.ttf"
SEED=20
NUM_WORKERS=6

# ============================================================
# Parse arguments
# ============================================================
if [ $# -lt 2 ]; then
    echo "Usage: $0 <start_line> <end_line> [orientation]"
    echo ""
    echo "Arguments:"
    echo "  start_line    Starting line number (0-indexed)"
    echo "  end_line      Ending line number (exclusive)"
    echo "  orientation   'h' for horizontal (default), 'v' for vertical"
    echo ""
    echo "Example:"
    echo "  $0 0 100000 h        # Process lines 0-99999, horizontal"
    echo "  $0 100000 200000 v   # Process lines 100000-199999, vertical"
    exit 1
fi

START_LINE=$1
END_LINE=$2
ORIENTATION=${3:-h}

# Validate orientation
if [ "$ORIENTATION" != "h" ] && [ "$ORIENTATION" != "v" ]; then
    echo "Error: orientation must be 'h' or 'v'"
    exit 1
fi

# Set output directory based on orientation
if [ "$ORIENTATION" = "h" ]; then
    OUT_DIR="$OUT_DIR_H"
    ORIENT_NAME="Horizontal"
    VERTICAL_FLAG=""
else
    OUT_DIR="$OUT_DIR_V"
    ORIENT_NAME="Vertical"
    VERTICAL_FLAG="--vertical"
fi

# ============================================================
# Display configuration
# ============================================================
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            Single Batch OCR Synthesis Runner                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Lines file:      $LINES_FILE"
echo "  Line range:      $START_LINE to $END_LINE"
echo "  Orientation:     $ORIENT_NAME ($ORIENTATION)"
echo "  Output dir:      $OUT_DIR"
echo "  Images/line:     $N_PER_LINE"
echo "  Workers:         $NUM_WORKERS"
echo ""

# ============================================================
# Preflight checks
# ============================================================
echo "Running preflight checks..."

if [ ! -f "$LINES_FILE" ]; then
    echo "Error: Lines file '$LINES_FILE' not found"
    exit 1
fi

if [ ! -d "$FONTS_DIR" ]; then
    echo "Error: Fonts directory '$FONTS_DIR' not found"
    exit 1
fi

if [ ! -d "$BGS_DIR" ]; then
    echo "Error: Backgrounds directory '$BGS_DIR' not found"
    exit 1
fi

# Create output directory
mkdir -p "$OUT_DIR"

# Check line range
TOTAL_LINES=$(wc -l < "$LINES_FILE")
if [ "$END_LINE" -gt "$TOTAL_LINES" ]; then
    echo "Warning: end_line ($END_LINE) exceeds total lines ($TOTAL_LINES)"
    echo "         Will process up to line $TOTAL_LINES"
fi

echo "✓ Preflight checks passed"
echo ""

# ============================================================
# Calculate estimates
# ============================================================
NUM_LINES=$((END_LINE - START_LINE))
NUM_IMAGES=$((NUM_LINES * N_PER_LINE))
APPROX_SIZE_GB=$((NUM_IMAGES * 80 / 1024 / 1024))

echo "Estimates:"
echo "  Lines to process:  $NUM_LINES"
echo "  Images to generate: $NUM_IMAGES"
echo "  Approximate size:   ~${APPROX_SIZE_GB}GB"
echo ""

# Check available space
local_avail_gb=$(df -BG --output=avail "$OUT_DIR" 2>/dev/null | tail -1 | tr -d ' G' || echo "0")
echo "  Available space:    ${local_avail_gb}GB"

SAFETY_GB=$((APPROX_SIZE_GB * 3 / 2 + 10))
if [ "$local_avail_gb" -lt "$SAFETY_GB" ] 2>/dev/null; then
    echo ""
    echo "[WARNING] Low disk space: need ~${SAFETY_GB}GB (incl. safety), have ${local_avail_gb}GB"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted by user"
        exit 0
    fi
fi

echo ""
read -p "Start processing? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted by user"
    exit 0
fi

# ============================================================
# Run synthesis
# ============================================================
START_TIME=$(date +%s)
LOGFILE="logs/batch_${ORIENTATION}_${START_LINE}_${END_LINE}_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   Starting Synthesis                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Log file: $LOGFILE"
echo ""

# Generate manifest filename
MANIFEST="${OUT_DIR}/manifest_${ORIENTATION}_${START_LINE}_${END_LINE}.jsonl"
ERROR_LOG="${OUT_DIR}/error_log_${ORIENTATION}_${START_LINE}_${END_LINE}.txt"

# Build command
CMD="python3 synth.py \
    --lines $LINES_FILE \
    --fonts_dir $FONTS_DIR \
    --bgs_dir $BGS_DIR \
    --out_dir $OUT_DIR \
    --manifest $MANIFEST \
    --error_log $ERROR_LOG \
    --n_per_line $N_PER_LINE \
    --box_jitter $BOX_JITTER \
    --no_debug_boxes \
    --last_resort_font $LAST_RESORT_FONT \
    --seed $SEED \
    --num_workers $NUM_WORKERS \
    --start_line $START_LINE \
    --end_line $END_LINE \
    $VERTICAL_FLAG"

echo "Executing: $CMD"
echo ""

# Run with logging
if eval "$CMD" 2>&1 | tee -a "$LOGFILE"; then
    EXIT_CODE=0
else
    EXIT_CODE=$?
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))
SECONDS=$((DURATION % 60))

# ============================================================
# Summary
# ============================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     Batch Complete                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Summary:"
echo "  Orientation:     $ORIENT_NAME"
echo "  Line range:      $START_LINE - $END_LINE"
echo "  Duration:        ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo "  Exit code:       $EXIT_CODE"
echo ""

# Count generated images
if [ -f "$MANIFEST" ]; then
    IMG_COUNT=$(wc -l < "$MANIFEST")
    echo "  Images generated: $IMG_COUNT"
    echo "  Manifest:        $MANIFEST"
fi

# Check for errors
if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
    ERR_COUNT=$(wc -l < "$ERROR_LOG")
    echo "  Errors:          $ERR_COUNT (see $ERROR_LOG)"
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Batch completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  - Run next batch with: $0 $END_LINE <next_end_line> $ORIENTATION"
    echo "  - When all batches done, merge manifests with: ./merge_manifests.py"
else
    echo "✗ Batch failed with exit code $EXIT_CODE"
    echo "  Check log file: $LOGFILE"
fi

echo ""

exit $EXIT_CODE
