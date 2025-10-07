#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch processing script for large-scale OCR synthesis.
Splits workload into manageable chunks to avoid memory issues.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def count_lines(filepath: Path) -> int:
    """Count number of non-empty lines in file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())


def run_batch(
    lines_file: str,
    fonts_dir: str,
    bgs_dir: str,
    out_dir: str,
    n_per_line: int,
    vertical: bool,
    box_jitter: str,
    last_resort_font: str,
    seed: int,
    num_workers: int,
    start_line: int,
    end_line: int,
) -> int:
    """Run synth.py for a specific line range."""
    cmd = [
        "python3", "synth.py",
        "--lines", lines_file,
        "--fonts_dir", fonts_dir,
        "--bgs_dir", bgs_dir,
        "--out_dir", out_dir,
        "--n_per_line", str(n_per_line),
        "--box_jitter", box_jitter,
        "--no_debug_boxes",
        "--last_resort_font", last_resort_font,
        "--seed", str(seed),
        "--num_workers", str(num_workers),
        "--start_line", str(start_line),
        "--end_line", str(end_line),
    ]

    if vertical:
        cmd.append("--vertical")

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Batch processor for OCR synthesis - splits large jobs into manageable chunks"
    )

    # Input/output
    parser.add_argument("--lines", type=str, default="lines.txt", help="Text lines file")
    parser.add_argument("--fonts_dir", type=str, default="fonts", help="Fonts directory")
    parser.add_argument("--bgs_dir", type=str, default="backgrounds", help="Backgrounds directory")
    parser.add_argument("--out_dir", type=str, default="out_h", help="Output directory")

    # Generation parameters
    parser.add_argument("--n_per_line", type=int, default=20, help="Number of images per line")
    parser.add_argument("--vertical", action="store_true", help="Generate vertical text")
    parser.add_argument("--box_jitter", type=str, default="2,2", help="Box jitter (x,y)")
    parser.add_argument("--last_resort_font", type=str, default="NotoSansTC-Regular.ttf", help="Last resort font")
    parser.add_argument("--seed", type=int, default=20, help="Random seed")
    parser.add_argument("--num_workers", type=int, default=6, help="Number of workers per batch")

    # Batch processing
    parser.add_argument("--batch_size", type=int, default=10000, help="Lines per batch (default: 10000)")

    args = parser.parse_args()

    # Count total lines
    lines_path = Path(args.lines)
    if not lines_path.exists():
        print(f"Error: Lines file '{args.lines}' not found")
        sys.exit(1)

    total_lines = count_lines(lines_path)
    print(f"Total lines in {args.lines}: {total_lines}")

    # Calculate batches
    num_batches = (total_lines + args.batch_size - 1) // args.batch_size
    print(f"\nConfiguration:")
    print(f"  Orientation: {'vertical' if args.vertical else 'horizontal'}")
    print(f"  Output directory: {args.out_dir}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Number of batches: {num_batches}")
    print(f"  Workers per batch: {args.num_workers}")
    print()

    # Create output directory
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)

    # Process each batch
    failed_batches = []
    for batch_idx in range(num_batches):
        start_line = batch_idx * args.batch_size
        end_line = min((batch_idx + 1) * args.batch_size, total_lines)

        print("=" * 60)
        print(f"Processing batch {batch_idx + 1}/{num_batches}")
        print(f"Lines: {start_line} to {end_line}")
        print("=" * 60)

        returncode = run_batch(
            lines_file=args.lines,
            fonts_dir=args.fonts_dir,
            bgs_dir=args.bgs_dir,
            out_dir=args.out_dir,
            n_per_line=args.n_per_line,
            vertical=args.vertical,
            box_jitter=args.box_jitter,
            last_resort_font=args.last_resort_font,
            seed=args.seed,
            num_workers=args.num_workers,
            start_line=start_line,
            end_line=end_line,
        )

        if returncode != 0:
            print(f"\n[ERROR] Batch {batch_idx + 1} failed with return code {returncode}")
            failed_batches.append(batch_idx + 1)
        else:
            print(f"\nBatch {batch_idx + 1}/{num_batches} completed successfully")
        print()

    # Summary
    print("=" * 60)
    if failed_batches:
        print(f"WARNING: {len(failed_batches)} batch(es) failed: {failed_batches}")
        print("Please check the error messages above and retry failed batches")
        sys.exit(1)
    else:
        print("All batches completed successfully!")
        print(f"Output saved to: {args.out_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
