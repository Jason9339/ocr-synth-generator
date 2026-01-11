# Data Directory

This directory is for storing your text data files.

## Usage

Place your text files here with one sentence per line:

```
data/
├── lines.txt           # Your main text data
├── test_data.txt       # Test data
└── custom_data.txt     # Custom data
```

## Example

Create a text file:

```bash
cat > data/my_text.txt << EOF
第一行範例文字
第二行範例文字
第三行範例文字
EOF
```

Then use it for generation:

```bash
python3 src/synth.py \
    --lines data/my_text.txt \
    --fonts_dir fonts \
    --bgs_dir backgrounds \
    --out_dir output/my_output \
    --manifest output/my_output/manifest.jsonl \
    --n_per_line 10
```

## Note

This directory is excluded from version control (see `.gitignore`).
Your text files will not be committed to the repository.
