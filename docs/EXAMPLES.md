# Usage Examples

This document provides practical examples for common use cases.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Historical Document Simulation](#historical-document-simulation)
- [Custom Configuration](#custom-configuration)
- [Large-Scale Generation](#large-scale-generation)
- [Integration with Training Pipeline](#integration-with-training-pipeline)

## Basic Usage

### Generate 100 Images from a Text File

```bash
# Create a sample text file
cat > sample.txt << EOF
繁體中文文字辨識測試
古籍文獻數位化研究
歷史文件辨識系統
EOF

# Generate horizontal layout
python3 synth.py \
    --lines sample.txt \
    --fonts_dir fonts \
    --bgs_dir backgrounds \
    --out_dir output/demo \
    --manifest output/demo/manifest.jsonl \
    --n_per_line 5 \
    --num_workers 2
```

This will generate 15 images (3 lines × 5 images per line).

### Generate Both Horizontal and Vertical Layouts

```bash
# Horizontal
python3 synth.py \
    --lines sample.txt \
    --out_dir output/horizontal \
    --manifest output/horizontal/manifest.jsonl \
    --n_per_line 10

# Vertical
python3 synth.py \
    --lines sample.txt \
    --out_dir output/vertical \
    --manifest output/vertical/manifest.jsonl \
    --n_per_line 10 \
    --vertical
```

## Historical Document Simulation

### Simulate Aged Paper with Degradation

To simulate historical documents, ensure your `backgrounds/` directory contains:
- Aged paper textures
- Stains and discoloration
- Low-contrast backgrounds

```bash
# The generator automatically applies:
# - Random background selection
# - Zoom jitter (1.0-1.15x)
# - Blur effects (sigma 0.2-0.9)
# - Variable text grayscale

python3 synth.py \
    --lines historical_texts.txt \
    --out_dir output/historical \
    --manifest output/historical/manifest.jsonl \
    --n_per_line 20 \
    --vertical
```

### Use Specific Archaic Character Sets

```bash
# Prepare a text file with archaic variants
cat > archaic.txt << EOF
臺灣總督府檔案
羅家倫先生文書
舊版字形測試樣本
EOF

python3 synth.py \
    --lines archaic.txt \
    --out_dir output/archaic \
    --manifest output/archaic/manifest.jsonl \
    --n_per_line 15
```

## Custom Configuration

### Add Debug Bounding Boxes

Useful for development and debugging:

```bash
python3 synth.py \
    --lines sample.txt \
    --out_dir output/debug \
    --manifest output/debug/manifest.jsonl \
    --debug_boxes \
    --n_per_line 5
```

### Add Box Jitter for Realistic Layouts

```bash
python3 synth.py \
    --lines sample.txt \
    --out_dir output/jittered \
    --manifest output/jittered/manifest.jsonl \
    --box_jitter 3,3 \
    --n_per_line 10
```

### Specify Fallback Font

```bash
python3 synth.py \
    --lines sample.txt \
    --out_dir output/custom_font \
    --manifest output/custom_font/manifest.jsonl \
    --last_resort_font "NotoSerifTC-Regular.ttf" \
    --n_per_line 10
```

### Set Random Seed for Reproducibility

```bash
python3 synth.py \
    --lines sample.txt \
    --out_dir output/reproducible \
    --manifest output/reproducible/manifest.jsonl \
    --seed 42 \
    --n_per_line 10
```

### Monitor Progress

```bash
# Check number of generated images
ls output/ocr_out_h/*.jpg | wc -l

# Check manifest entries
wc -l output/ocr_out_h/manifest_h_*.jsonl

# Check disk usage
du -sh output/
```

## Integration with Training Pipeline

### Example 1: PyTorch Dataset

```python
import json
from PIL import Image
from torch.utils.data import Dataset

class SyntheticOCRDataset(Dataset):
    def __init__(self, manifest_path, transform=None):
        self.transform = transform
        self.samples = []

        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line in f:
                self.samples.append(json.loads(line))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        image = Image.open(sample['image_path']).convert('RGB')
        text = sample['text']

        if self.transform:
            image = self.transform(image)

        return image, text

# Usage
dataset = SyntheticOCRDataset('output/horizontal/manifest.jsonl')
```

### Example 2: LMDB Dataset

```python
import lmdb
import pickle
from PIL import Image
from io import BytesIO

class LMDBDataset(Dataset):
    def __init__(self, lmdb_path):
        self.env = lmdb.open(lmdb_path, readonly=True, lock=False)

        with self.env.begin() as txn:
            self.length = txn.stat()['entries']

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        with self.env.begin() as txn:
            key = f'{idx:08d}'.encode()
            data = pickle.loads(txn.get(key))

            image = Image.open(BytesIO(data['image']))
            text = data['text']

            return image, text

# Usage
dataset = LMDBDataset('output_h.lmdb')
```

### Example 3: Streaming from Hugging Face

```python
from datasets import load_dataset

# Load the pre-generated dataset
dataset = load_dataset("ZihCiLin/traditional-chinese-ocr-synthetic", split="train")

# Stream without downloading the entire dataset
dataset = load_dataset(
    "ZihCiLin/traditional-chinese-ocr-synthetic",
    split="train",
    streaming=True
)

for sample in dataset:
    image = sample['image']
    text = sample['text']
    # Process...
```

## Advanced Examples

### Filter Manifest by Orientation

```bash
# Extract only vertical text samples
jq 'select(.orientation == "vertical")' output/manifest.jsonl > vertical_only.jsonl

# Count by orientation
jq -r '.orientation' output/manifest.jsonl | sort | uniq -c
```

### Analyze Character Distribution

```python
import json
from collections import Counter

def analyze_characters(manifest_path):
    char_counter = Counter()

    with open(manifest_path, 'r', encoding='utf-8') as f:
        for line in f:
            sample = json.loads(line)
            char_counter.update(sample['text'])

    # Print top 20 most common characters
    for char, count in char_counter.most_common(20):
        print(f'{char}: {count}')

analyze_characters('output/horizontal/manifest.jsonl')
```

### Split Dataset for Training/Validation

```python
import json
import random

def split_manifest(manifest_path, train_ratio=0.9, seed=42):
    random.seed(seed)

    with open(manifest_path, 'r', encoding='utf-8') as f:
        samples = [json.loads(line) for line in f]

    random.shuffle(samples)

    split_idx = int(len(samples) * train_ratio)
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:]

    with open('train_manifest.jsonl', 'w', encoding='utf-8') as f:
        for sample in train_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    with open('val_manifest.jsonl', 'w', encoding='utf-8') as f:
        for sample in val_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    print(f'Train: {len(train_samples)}, Val: {len(val_samples)}')

split_manifest('output/horizontal/manifest.jsonl')
```

## Troubleshooting Examples

### Check Font Coverage

```bash
python3 check_fonts.py
```

### Verify Generated Images

```bash
# Check if images can be opened
python3 check_images.py output/horizontal/
```

### Validate LMDB

```bash
python3 convert_to_lmdb.py \
    --src output/horizontal \
    --dst test.lmdb \
    --verify
```

## Performance Optimization

### Maximize Throughput

```bash
# Use more workers (adjust based on CPU cores)
python3 synth.py \
    --lines large_dataset.txt \
    --out_dir output/fast \
    --manifest output/fast/manifest.jsonl \
    --num_workers 12 \
    --n_per_line 20
```

### Reduce Memory Usage

```bash
# Process smaller batches
./run_single_batch.sh 0 1000 h
./run_single_batch.sh 1000 2000 h
# ... continue
```

---

For more examples and use cases, please refer to the [main README](README.md) or open an issue on GitHub.
