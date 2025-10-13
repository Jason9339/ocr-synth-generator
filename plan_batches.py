#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch execution planner - generates command lists for manual batch execution.
"""

import argparse
from pathlib import Path


def count_lines(filepath: Path) -> int:
    """Count number of non-empty lines in file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())


def plan_batches(total_lines: int, batch_size: int) -> list:
    """
    Generate batch ranges.

    Args:
        total_lines: Total number of lines
        batch_size: Lines per batch

    Returns:
        List of (start, end) tuples
    """
    batches = []
    start = 0
    while start < total_lines:
        end = min(start + batch_size, total_lines)
        batches.append((start, end))
        start = end
    return batches


def print_execution_plan(batches: list, orientation: str):
    """Print execution commands for batches."""
    orient_name = "Horizontal" if orientation == "h" else "Vertical"
    print(f"\n{'=' * 60}")
    print(f"{orient_name} Batches ({orientation}):")
    print(f"{'=' * 60}")

    for i, (start, end) in enumerate(batches, 1):
        num_lines = end - start
        print(f"# Batch {i}: Lines {start:,} to {end:,} ({num_lines:,} lines)")
        print(f"./run_single_batch.sh {start} {end} {orientation}")
        print()


def generate_bash_script(batches_h: list, batches_v: list, output_file: str):
    """Generate a bash script for sequential execution."""
    with open(output_file, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Auto-generated batch execution plan\n")
        f.write("# WARNING: This will run ALL batches sequentially!\n")
        f.write("# Estimated time: Several hours to days depending on data size\n")
        f.write("\n")
        f.write("set -euo pipefail\n")
        f.write("\n")
        f.write("echo \"Starting batch execution plan...\"\n")
        f.write("echo \"Total batches: {} horizontal + {} vertical = {} total\"\n".format(
            len(batches_h), len(batches_v), len(batches_h) + len(batches_v)
        ))
        f.write("echo \"\"\n")
        f.write("\n")

        # Horizontal batches
        f.write("# ============================================================\n")
        f.write("# Horizontal Batches\n")
        f.write("# ============================================================\n")
        f.write("\n")

        for i, (start, end) in enumerate(batches_h, 1):
            f.write(f"echo \"Executing horizontal batch {i}/{len(batches_h)}...\"\n")
            f.write(f"./run_single_batch.sh {start} {end} h\n")
            f.write(f"if [ $? -ne 0 ]; then\n")
            f.write(f"    echo \"ERROR: Horizontal batch {i} failed!\"\n")
            f.write(f"    exit 1\n")
            f.write(f"fi\n")
            f.write("\n")

        # Vertical batches
        f.write("# ============================================================\n")
        f.write("# Vertical Batches\n")
        f.write("# ============================================================\n")
        f.write("\n")

        for i, (start, end) in enumerate(batches_v, 1):
            f.write(f"echo \"Executing vertical batch {i}/{len(batches_v)}...\"\n")
            f.write(f"./run_single_batch.sh {start} {end} v\n")
            f.write(f"if [ $? -ne 0 ]; then\n")
            f.write(f"    echo \"ERROR: Vertical batch {i} failed!\"\n")
            f.write(f"    exit 1\n")
            f.write(f"fi\n")
            f.write("\n")

        # Merge manifests
        f.write("# ============================================================\n")
        f.write("# Merge Manifests\n")
        f.write("# ============================================================\n")
        f.write("\n")
        f.write("echo \"Merging manifests...\"\n")
        f.write("python3 merge_manifests.py --merge-both\n")
        f.write("\n")
        f.write("echo \"All batches completed successfully!\"\n")
        f.write("echo \"Next steps:\"\n")
        f.write("echo \"  1. Convert to LMDB\"\n")
        f.write("echo \"  2. Transfer to NFS\"\n")
        f.write("echo \"  3. Clean up local images\"\n")

    # Make executable
    Path(output_file).chmod(0o755)


def main():
    parser = argparse.ArgumentParser(
        description="Plan batch execution for manual processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Plan batches for 34,413 lines with default 100k batch size
  python3 plan_batches.py

  # Use 50k batch size for more frequent checkpoints
  python3 plan_batches.py --batch-size 50000

  # Generate executable script (use with caution!)
  python3 plan_batches.py --generate-script auto_run.sh
        """
    )

    parser.add_argument(
        "--lines",
        type=str,
        default="lines.txt",
        help="Input text file (default: lines.txt)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100000,
        help="Lines per batch (default: 100000)"
    )

    parser.add_argument(
        "--generate-script",
        type=str,
        help="Generate bash script for sequential execution (use with caution!)"
    )

    args = parser.parse_args()

    # Count lines
    lines_path = Path(args.lines)
    if not lines_path.exists():
        print(f"Error: Lines file '{args.lines}' not found")
        return 1

    total_lines = count_lines(lines_path)

    # Plan batches
    batches = plan_batches(total_lines, args.batch_size)

    # Display plan
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║                  Batch Execution Planner                       ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    print(f"Input file:        {args.lines}")
    print(f"Total lines:       {total_lines:,}")
    print(f"Batch size:        {args.batch_size:,}")
    print(f"Number of batches: {len(batches)}")
    print()

    # Calculate estimates
    images_per_batch = args.batch_size * 20  # default n_per_line
    total_images = total_lines * 20 * 2  # both orientations
    gb_per_batch = images_per_batch * 80 / (1024 * 1024)
    total_gb = total_images * 80 / (1024 * 1024)

    print(f"Estimates:")
    print(f"  Images per batch:  {images_per_batch:,}")
    print(f"  Size per batch:    ~{gb_per_batch:.1f} GB")
    print(f"  Total images:      {total_images:,} (H + V)")
    print(f"  Total size:        ~{total_gb:.1f} GB")
    print()

    # Print execution plans
    print_execution_plan(batches, 'h')
    print_execution_plan(batches, 'v')

    # Print merge command
    print(f"{'=' * 60}")
    print("After all batches complete, merge manifests:")
    print(f"{'=' * 60}")
    print()
    print("python3 merge_manifests.py --merge-both")
    print()

    # Generate script if requested
    if args.generate_script:
        generate_bash_script(batches, batches, args.generate_script)
        print(f"{'=' * 60}")
        print(f"Generated execution script: {args.generate_script}")
        print(f"{'=' * 60}")
        print()
        print("⚠️  WARNING: This script will run ALL batches sequentially!")
        print("   This may take many hours and could still be interrupted by system.")
        print("   It's recommended to run batches manually instead.")
        print()
        print(f"To execute: ./{args.generate_script}")
        print()

    # Print recommendations
    print(f"{'=' * 60}")
    print("Recommendations:")
    print(f"{'=' * 60}")
    print()
    print("1. Execute batches one by one manually")
    print("2. Monitor each batch completion before starting next")
    print("3. If interrupted, restart from the failed batch")
    print("4. After all batches complete, run merge_manifests.py")
    print()

    # Time estimates
    minutes_per_batch = args.batch_size * 20 * 2 / 1000  # rough estimate
    hours_per_orientation = len(batches) * minutes_per_batch / 60
    total_hours = hours_per_orientation * 2

    print(f"Rough time estimates (may vary):")
    print(f"  Per batch:           ~{minutes_per_batch:.0f} minutes")
    print(f"  Per orientation:     ~{hours_per_orientation:.1f} hours")
    print(f"  Total (both):        ~{total_hours:.1f} hours")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
