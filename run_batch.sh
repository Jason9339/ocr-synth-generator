#!/bin/bash
# Master batch processing script for OCR synthesis
# Runs both horizontal and vertical text generation sequentially

set -euo pipefail
mkdir -p logs
exec > >(tee -a logs/master_$(date +%Y%m%d_%H%M%S).log) 2>&1
trap 'echo "[FATAL] Script stopped unexpectedly at $(date)" >> logs/master_$(date +%Y%m%d_%H%M%S).log' ERR

# Default configuration
LINES_FILE="lines.txt"
FONTS_DIR="fonts"
BGS_DIR="backgrounds"
OUT_DIR_H="out_h"
OUT_DIR_V="out_v"
N_PER_LINE=20
BOX_JITTER="2,2"
LAST_RESORT_FONT="NotoSansTC-Regular.ttf"
SEED=20
NUM_WORKERS=6
BATCH_SIZE=10000

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --lines)
            LINES_FILE="$2"
            shift 2
            ;;
        --fonts_dir)
            FONTS_DIR="$2"
            shift 2
            ;;
        --bgs_dir)
            BGS_DIR="$2"
            shift 2
            ;;
        --out_dir_h)
            OUT_DIR_H="$2"
            shift 2
            ;;
        --out_dir_v)
            OUT_DIR_V="$2"
            shift 2
            ;;
        --n_per_line)
            N_PER_LINE="$2"
            shift 2
            ;;
        --box_jitter)
            BOX_JITTER="$2"
            shift 2
            ;;
        --last_resort_font)
            LAST_RESORT_FONT="$2"
            shift 2
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        --num_workers)
            NUM_WORKERS="$2"
            shift 2
            ;;
        --batch_size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Master script to run both horizontal and vertical OCR synthesis"
            echo ""
            echo "Options:"
            echo "  --lines LINES_FILE            Input text file (default: lines.txt)"
            echo "  --fonts_dir FONTS_DIR         Fonts directory (default: fonts)"
            echo "  --bgs_dir BGS_DIR             Backgrounds directory (default: backgrounds)"
            echo "  --out_dir_h OUT_DIR_H         Horizontal output directory (default: out_h)"
            echo "  --out_dir_v OUT_DIR_V         Vertical output directory (default: out_v)"
            echo "  --n_per_line N                Images per line (default: 20)"
            echo "  --box_jitter X,Y              Box jitter (default: 2,2)"
            echo "  --last_resort_font FONT       Last resort font (default: NotoSansTC-Regular.ttf)"
            echo "  --seed SEED                   Random seed (default: 20)"
            echo "  --num_workers N               Workers per batch (default: 6)"
            echo "  --batch_size N                Lines per batch (default: 10000)"
            echo "  --help                        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          OCR Synthesis - Master Batch Processing              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Lines file:          $LINES_FILE"
echo "  Fonts directory:     $FONTS_DIR"
echo "  Backgrounds:         $BGS_DIR"
echo "  Output (horizontal): $OUT_DIR_H"
echo "  Output (vertical):   $OUT_DIR_V"
echo "  Images per line:     $N_PER_LINE"
echo "  Batch size:          $BATCH_SIZE"
echo "  Workers per batch:   $NUM_WORKERS"
echo "  Random seed:         $SEED"
echo ""

# Check if files exist
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

# Count total lines
TOTAL_LINES=$(wc -l < "$LINES_FILE")
echo "Total lines to process: $TOTAL_LINES"
echo ""

# Calculate total images and approximate size
TOTAL_IMAGES_PER_ORIENTATION=$((TOTAL_LINES * N_PER_LINE))
TOTAL_IMAGES=$((TOTAL_IMAGES_PER_ORIENTATION * 2))
APPROX_SIZE_GB=$((TOTAL_IMAGES * 80 / 1024 / 1024))  # Assume ~80KB per image

echo "Estimated output:"
echo "  Images per orientation: $TOTAL_IMAGES_PER_ORIENTATION"
echo "  Total images (H+V):     $TOTAL_IMAGES"
echo "  Approximate size:       ~${APPROX_SIZE_GB}GB"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted by user"
    exit 0
fi

START_TIME=$(date +%s)

# ============================================================
# Part 1: Horizontal text generation
# ============================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  PART 1: Horizontal Text                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

python3 run_batch.py \
    --lines "$LINES_FILE" \
    --fonts_dir "$FONTS_DIR" \
    --bgs_dir "$BGS_DIR" \
    --out_dir "$OUT_DIR_H" \
    --n_per_line $N_PER_LINE \
    --box_jitter "$BOX_JITTER" \
    --last_resort_font "$LAST_RESORT_FONT" \
    --seed $SEED \
    --num_workers $NUM_WORKERS \
    --batch_size $BATCH_SIZE

if [ $? -ne 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    ERROR: Horizontal Failed                    ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    exit 1
fi

echo ""
echo "✓ Horizontal text generation completed!"
echo ""

# ============================================================
# Part 2: Vertical text generation
# ============================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   PART 2: Vertical Text                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

python3 run_batch.py \
    --lines "$LINES_FILE" \
    --fonts_dir "$FONTS_DIR" \
    --bgs_dir "$BGS_DIR" \
    --out_dir "$OUT_DIR_V" \
    --n_per_line $N_PER_LINE \
    --vertical \
    --box_jitter "$BOX_JITTER" \
    --last_resort_font "$LAST_RESORT_FONT" \
    --seed $SEED \
    --num_workers $NUM_WORKERS \
    --batch_size $BATCH_SIZE

if [ $? -ne 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                     ERROR: Vertical Failed                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    exit 1
fi

echo ""
echo "✓ Vertical text generation completed!"
echo ""

# ============================================================
# Summary
# ============================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ALL PROCESSING COMPLETE!                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Summary:"
echo "  Horizontal output: $OUT_DIR_H"
echo "  Vertical output:   $OUT_DIR_V"
echo "  Total duration:    ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo ""

# Count generated files
H_COUNT=$(find "$OUT_DIR_H" -name "*.jpg" 2>/dev/null | wc -l)
V_COUNT=$(find "$OUT_DIR_V" -name "*.jpg" 2>/dev/null | wc -l)

echo "Generated images:"
echo "  Horizontal: $H_COUNT"
echo "  Vertical:   $V_COUNT"
echo "  Total:      $((H_COUNT + V_COUNT))"
echo ""

# Merge batch manifests
echo "Merging batch manifests..."
if ls "$OUT_DIR_H"/manifest_h_*.jsonl 1> /dev/null 2>&1; then
    cat "$OUT_DIR_H"/manifest_h_*.jsonl > "$OUT_DIR_H/manifest_h_all.jsonl"
    H_MANIFEST_COUNT=$(wc -l < "$OUT_DIR_H/manifest_h_all.jsonl")
    echo "  Horizontal manifest: $H_MANIFEST_COUNT entries → $OUT_DIR_H/manifest_h_all.jsonl"
fi

if ls "$OUT_DIR_V"/manifest_v_*.jsonl 1> /dev/null 2>&1; then
    cat "$OUT_DIR_V"/manifest_v_*.jsonl > "$OUT_DIR_V/manifest_v_all.jsonl"
    V_MANIFEST_COUNT=$(wc -l < "$OUT_DIR_V/manifest_v_all.jsonl")
    echo "  Vertical manifest:   $V_MANIFEST_COUNT entries → $OUT_DIR_V/manifest_v_all.jsonl"
fi
echo ""

# Check for errors across all batch error logs
H_ERRORS=0
if ls "$OUT_DIR_H"/error_log_h_*.txt 1> /dev/null 2>&1; then
    for error_file in "$OUT_DIR_H"/error_log_h_*.txt; do
        if [ -s "$error_file" ]; then
            FILE_ERRORS=$(wc -l < "$error_file")
            H_ERRORS=$((H_ERRORS + FILE_ERRORS))
        fi
    done
    if [ $H_ERRORS -gt 0 ]; then
        echo "⚠ Warning: $H_ERRORS total errors in horizontal batches"
        echo "  Error logs: $OUT_DIR_H/error_log_h_*.txt"
    fi
fi

V_ERRORS=0
if ls "$OUT_DIR_V"/error_log_v_*.txt 1> /dev/null 2>&1; then
    for error_file in "$OUT_DIR_V"/error_log_v_*.txt; do
        if [ -s "$error_file" ]; then
            FILE_ERRORS=$(wc -l < "$error_file")
            V_ERRORS=$((V_ERRORS + FILE_ERRORS))
        fi
    done
    if [ $V_ERRORS -gt 0 ]; then
        echo "⚠ Warning: $V_ERRORS total errors in vertical batches"
        echo "  Error logs: $OUT_DIR_V/error_log_v_*.txt"
    fi
fi

if [ $H_ERRORS -eq 0 ] && [ $V_ERRORS -eq 0 ]; then
    echo "✓ No errors detected"
fi

echo ""
echo "Next steps:"
echo "  1. Check error logs (if any): ls -lh $OUT_DIR_H/error_log_*.txt"
echo "  2. Verify output images: ls -lh $OUT_DIR_H/*.jpg | head"
echo "  3. Review merged manifests:"
echo "     - head $OUT_DIR_H/manifest_h_all.jsonl"
echo "     - head $OUT_DIR_V/manifest_v_all.jsonl"
echo ""
