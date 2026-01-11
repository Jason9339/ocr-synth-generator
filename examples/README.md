# Examples

This directory contains sample data for testing the OCR synthesis generator.

## Sample Files

### `sample_lines.txt`

A sample text file containing 10 Traditional Chinese sentences. Use this to test the generator:

```bash
# Generate 20 images (10 lines × 2 images per line)
python3 ../src/synth.py \
    --lines sample_lines.txt \
    --fonts_dir ../fonts \
    --bgs_dir ../backgrounds \
    --out_dir ../output/sample_horizontal \
    --manifest ../output/sample_horizontal/manifest.jsonl \
    --n_per_line 2 \
    --num_workers 2

# Generate vertical layout
python3 ../src/synth.py \
    --lines sample_lines.txt \
    --fonts_dir ../fonts \
    --bgs_dir ../backgrounds \
    --out_dir ../output/sample_vertical \
    --manifest ../output/sample_vertical/manifest.jsonl \
    --n_per_line 2 \
    --vertical \
    --num_workers 2
```

## Quick Test

To quickly verify the installation works:

```bash
cd examples
python3 ../scripts/check_fonts.py
```

## Creating Your Own Data

1. Create a text file with one sentence per line:
   ```
   第一行文字
   第二行文字
   第三行文字
   ```

2. Save it as `my_lines.txt`

3. Run the generator:
   ```bash
   python3 ../src/synth.py \
       --lines my_lines.txt \
       --fonts_dir ../fonts \
       --bgs_dir ../backgrounds \
       --out_dir ../output/my_output \
       --manifest ../output/my_output/manifest.jsonl \
       --n_per_line 10
   ```

For more examples, see [docs/EXAMPLES.md](../docs/EXAMPLES.md).
