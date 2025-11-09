# README - Plan 2: Balanced Character Frequency OCR Dataset

## 🎯 Overview

Plan 2 generates OCR training data where **all 13,172 unique characters** appear at least **150 times**, ensuring balanced representation for rare and common characters alike.

## ✅ What's Been Done

1. ✅ Generated `lines2.txt` (68,142 lines, 5.1 MB)
2. ✅ All characters now have ≥150 occurrences
3. ✅ Created batch processing scripts
4. ✅ Complete documentation

## 📁 Key Files

| File | Purpose |
|------|---------|
| `lines2.txt` | Generated balanced data (68,142 lines) |
| `run_single_batch2.sh` | Batch processing script |
| `BATCH_QUICK_START2.md` | **START HERE** - Quick batch commands |
| `BATCH_PLAN2.md` | Detailed batch processing plan |

## 🚀 Quick Start

### 1. Test the Script

```bash
./run_single_batch2.sh 0 100 h
```

### 2. Run Recommended Batch Plan

**Medium batches (10,000 lines each) - RECOMMENDED**

#### Horizontal Images:
```bash
./run_single_batch2.sh 0 10000 h
./run_single_batch2.sh 10000 20000 h
./run_single_batch2.sh 20000 30000 h
./run_single_batch2.sh 30000 40000 h
./run_single_batch2.sh 40000 50000 h
./run_single_batch2.sh 50000 60000 h
./run_single_batch2.sh 60000 68142 h
```

#### Vertical Images:
```bash
./run_single_batch2.sh 0 10000 v
./run_single_batch2.sh 10000 20000 v
./run_single_batch2.sh 20000 30000 v
./run_single_batch2.sh 30000 40000 v
./run_single_batch2.sh 40000 50000 v
./run_single_batch2.sh 50000 60000 v
./run_single_batch2.sh 60000 68142 v
```

**Total**: 14 batches → ~681,420 images → ~60-80 GB

### 3. Alternative: Small Batches (5,000 lines)

See [BATCH_QUICK_START2.md](BATCH_QUICK_START2.md) for the full 28-batch breakdown.

## 📊 Statistics

### Character Frequency (lines2.txt combined with lines.txt)
- **Total characters**: 2,584,925
- **Unique characters**: 13,172
- **Characters at exactly 150**: 12,377 (93.9%)
- **Characters above 150**: 795 (6.1%)
- **Characters below 150**: 0 ✓

### Dataset Size
- **Lines**: 68,142
- **Images per line**: 5
- **Total images**: ~340,710 per orientation
- **Both orientations**: ~681,420 images
- **Disk space**: ~60-80 GB

## 🔧 Scripts

### `run_single_batch2.sh`

```bash
Usage: ./run_single_batch2.sh <start_line> <end_line> <orientation>

Arguments:
  start_line   : Starting line number (0-indexed)
  end_line     : Ending line number (exclusive)
  orientation  : h (horizontal) or v (vertical)

Example:
  ./run_single_batch2.sh 0 5000 h    # Lines 0-4999, horizontal
  ./run_single_batch2.sh 5000 10000 v # Lines 5000-9999, vertical
```

## 🗂️ Output Structure

```
out2_h_0_10000/          # Horizontal, lines 0-9999
├── 000000_h_0.jpg
├── 000000_h_1.jpg
├── ...
├── manifest.jsonl
└── error_log_h_0_10000.txt

out2_v_0_10000/          # Vertical, lines 0-9999
├── 000000_v_0.jpg
├── 000000_v_1.jpg
├── ...
├── manifest.jsonl
└── error_log_v_0_10000.txt
```

## 🔄 After Completion

### Merge Manifests
```bash
cat out2_h_*/manifest.jsonl > manifest_lines2_h.jsonl
cat out2_v_*/manifest.jsonl > manifest_lines2_v.jsonl
```

### Count Images
```bash
find out2_h_* -name "*.jpg" | wc -l  # Horizontal
find out2_v_* -name "*.jpg" | wc -l  # Vertical
```

### Check Size
```bash
du -sh out2_*
```