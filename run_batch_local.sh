#!/bin/bash
# Master batch processing script for OCR synthesis
# 全磁碟運行模式 - 不同步到 NFS，最後輸出報告

set -euo pipefail
mkdir -p logs
LOGTS="$(date +%Y%m%d_%H%M%S)"
LOGFILE="logs/master_${LOGTS}.log"
exec > >(tee -a "$LOGFILE") 2>&1
trap 'echo "[FATAL] Script stopped unexpectedly at $(date)" >> "$LOGFILE"' ERR

# Default configuration
LINES_FILE="lines.txt"
FONTS_DIR="fonts"
BGS_DIR="backgrounds"

# ★★★ 全部使用本機磁碟 ★★★
OUT_DIR_H="/ocr_out_h"
OUT_DIR_V="/ocr_out_v"

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
            echo "Master script for local-only OCR synthesis (no NFS sync)"
            echo ""
            echo "Options:"
            echo "  --lines LINES_FILE            Input text file (default: lines.txt)"
            echo "  --fonts_dir FONTS_DIR         Fonts directory (default: fonts)"
            echo "  --bgs_dir BGS_DIR             Backgrounds directory (default: backgrounds)"
            echo "  --out_dir_h OUT_DIR_H         Horizontal output directory (default: /ocr_out_h)"
            echo "  --out_dir_v OUT_DIR_V         Vertical output directory (default: /ocr_out_v)"
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
echo "║       OCR Synthesis - Local Disk Mode (No NFS Sync)           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Lines file:            $LINES_FILE"
echo "  Fonts directory:       $FONTS_DIR"
echo "  Backgrounds:           $BGS_DIR"
echo "  Output (H):            $OUT_DIR_H"
echo "  Output (V):            $OUT_DIR_V"
echo "  Images per line:       $N_PER_LINE"
echo "  Batch size:            $BATCH_SIZE"
echo "  Workers per batch:     $NUM_WORKERS"
echo "  Random seed:           $SEED"
echo ""

# ============================================================
# Preflight Checks
# ============================================================
echo "Running preflight checks..."

# Check if files/directories exist
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

# Ensure output paths are on local filesystem (not NFS)
for out_path in "$OUT_DIR_H" "$OUT_DIR_V"; do
    mkdir -p "$out_path"
    fs_type=$(stat -f -c %T "$out_path" 2>/dev/null || echo "unknown")

    if echo "$fs_type" | grep -qiE 'nfs|cifs|smb'; then
        echo "[FATAL] $out_path is on $fs_type (network filesystem)."
        echo "        This script is for local-disk-only mode."
        echo "        Expected: ext4, xfs, overlay, tmpfs, etc."
        exit 1
    fi

    echo "✓ $out_path is on local filesystem ($fs_type)"
done

# Check local available space (recommend at least 100GB for safety)
local_avail_gb=$(df -BG --output=avail "$OUT_DIR_H" 2>/dev/null | tail -1 | tr -d ' G' || echo "0")
if [ "$local_avail_gb" -lt 100 ] 2>/dev/null; then
    echo "⚠ WARNING: Local space ${local_avail_gb}GB < 100GB (recommended minimum)"
    echo "          Proceed with caution."
fi

echo "✓ Preflight checks passed"
echo ""

# Count total lines
TOTAL_LINES=$(wc -l < "$LINES_FILE")
echo "Total lines to process: $TOTAL_LINES"
echo ""

# Calculate total images
TOTAL_IMAGES_PER_ORIENTATION=$((TOTAL_LINES * N_PER_LINE))
TOTAL_IMAGES=$((TOTAL_IMAGES_PER_ORIENTATION * 2))
APPROX_SIZE_GB=$((TOTAL_IMAGES * 80 / 1024 / 1024))

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

if ! python3 run_batch.py \
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
then
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

if ! python3 run_batch.py \
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
then
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
# Generate Report
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

# Collect statistics
H_COUNT=$(cat "$OUT_DIR_H"/manifest_h_*.jsonl 2>/dev/null | wc -l | tr -d ' ' || echo "0")
V_COUNT=$(cat "$OUT_DIR_V"/manifest_v_*.jsonl 2>/dev/null | wc -l | tr -d ' ' || echo "0")
H_SIZE=$(du -sh "$OUT_DIR_H" 2>/dev/null | cut -f1 || echo "0")
V_SIZE=$(du -sh "$OUT_DIR_V" 2>/dev/null | cut -f1 || echo "0")

# Merge batch manifests
echo "Merging batch manifests..."
if ls "$OUT_DIR_H"/manifest_h_*.jsonl 1> /dev/null 2>&1; then
    cat "$OUT_DIR_H"/manifest_h_*.jsonl > "$OUT_DIR_H/manifest_h_all.jsonl"
    echo "  ✓ Horizontal manifest: $H_COUNT entries → $OUT_DIR_H/manifest_h_all.jsonl"
fi

if ls "$OUT_DIR_V"/manifest_v_*.jsonl 1> /dev/null 2>&1; then
    cat "$OUT_DIR_V"/manifest_v_*.jsonl > "$OUT_DIR_V/manifest_v_all.jsonl"
    echo "  ✓ Vertical manifest:   $V_COUNT entries → $OUT_DIR_V/manifest_v_all.jsonl"
fi
echo ""

# Check for errors
H_ERRORS=0
if ls "$OUT_DIR_H"/error_log_h_*.txt 1> /dev/null 2>&1; then
    for error_file in "$OUT_DIR_H"/error_log_h_*.txt; do
        if [ -s "$error_file" ]; then
            FILE_ERRORS=$(wc -l < "$error_file")
            H_ERRORS=$((H_ERRORS + FILE_ERRORS))
        fi
    done
fi

V_ERRORS=0
if ls "$OUT_DIR_V"/error_log_v_*.txt 1> /dev/null 2>&1; then
    for error_file in "$OUT_DIR_V"/error_log_v_*.txt; do
        if [ -s "$error_file" ]; then
            FILE_ERRORS=$(wc -l < "$error_file")
            V_ERRORS=$((V_ERRORS + FILE_ERRORS))
        fi
    done
fi

# Generate JSON report
REPORT_FILE="report_${LOGTS}.json"
cat > "$REPORT_FILE" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "duration_seconds": $DURATION,
  "duration_human": "${HOURS}h ${MINUTES}m ${SECONDS}s",
  "input": {
    "lines_file": "$LINES_FILE",
    "total_lines": $TOTAL_LINES,
    "images_per_line": $N_PER_LINE
  },
  "output": {
    "horizontal": {
      "directory": "$OUT_DIR_H",
      "image_count": $H_COUNT,
      "size": "$H_SIZE",
      "errors": $H_ERRORS
    },
    "vertical": {
      "directory": "$OUT_DIR_V",
      "image_count": $V_COUNT,
      "size": "$V_SIZE",
      "errors": $V_ERRORS
    },
    "total_images": $((H_COUNT + V_COUNT))
  },
  "config": {
    "batch_size": $BATCH_SIZE,
    "num_workers": $NUM_WORKERS,
    "seed": $SEED,
    "box_jitter": "$BOX_JITTER"
  }
}
EOF

echo "Summary:"
echo "  Horizontal images: $H_COUNT ($H_SIZE)"
echo "  Vertical images:   $V_COUNT ($V_SIZE)"
echo "  Total images:      $((H_COUNT + V_COUNT))"
echo "  Total duration:    ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo ""

if [ $H_ERRORS -eq 0 ] && [ $V_ERRORS -eq 0 ]; then
    echo "✓ No errors detected"
else
    [ $H_ERRORS -gt 0 ] && echo "⚠ Horizontal errors: $H_ERRORS"
    [ $V_ERRORS -gt 0 ] && echo "⚠ Vertical errors: $V_ERRORS"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    Report Generated                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Report saved to: $REPORT_FILE"
echo ""
echo "Next steps:"
echo "  1. Convert to LMDB:"
echo "     python3 convert_to_lmdb.py --src /ocr_out_h --dst out_h.lmdb"
echo "     python3 convert_to_lmdb.py --src /ocr_out_v --dst out_v.lmdb"
echo ""
echo "  2. Transfer LMDB files to NFS:"
echo "     rsync -a out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/"
echo ""
echo "  3. (Optional) Clean up local images:"
echo "     rm -rf /ocr_out_h /ocr_out_v"
echo ""
