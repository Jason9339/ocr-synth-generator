#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge multiple manifest files from batch processing into a single manifest.
This script combines all manifest_h_*.jsonl or manifest_v_*.jsonl files
into manifest_h_all.jsonl and manifest_v_all.jsonl respectively.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple


def find_manifest_files(directory: Path, orientation: str) -> List[Path]:
    """
    Find all manifest files for a given orientation.

    Args:
        directory: Directory to search
        orientation: 'h' for horizontal, 'v' for vertical

    Returns:
        List of manifest file paths, sorted by start line number
    """
    pattern = f"manifest_{orientation}_*.jsonl"
    manifests = list(directory.glob(pattern))

    # Exclude the merged manifest if it exists
    manifests = [m for m in manifests if m.name != f"manifest_{orientation}_all.jsonl"]

    if not manifests:
        return []

    # Sort by start line number (extracted from filename)
    def extract_start_line(path: Path) -> int:
        # manifest_h_0_100000.jsonl -> extract 0
        parts = path.stem.split('_')
        try:
            # Format: manifest_{orient}_{start}_{end}
            return int(parts[2])
        except (IndexError, ValueError):
            return 0

    manifests.sort(key=extract_start_line)
    return manifests


def merge_manifests(
    directory: Path,
    orientation: str,
    output_file: Path = None,
    verify: bool = True
) -> Tuple[int, int]:
    """
    Merge all manifest files for a given orientation.

    Args:
        directory: Directory containing manifest files
        orientation: 'h' for horizontal, 'v' for vertical
        output_file: Output file path (default: manifest_{orientation}_all.jsonl)
        verify: Whether to verify JSON format

    Returns:
        Tuple of (total_entries, total_errors)
    """
    manifests = find_manifest_files(directory, orientation)

    if not manifests:
        print(f"No manifest files found for orientation '{orientation}' in {directory}")
        return 0, 0

    if output_file is None:
        output_file = directory / f"manifest_{orientation}_all.jsonl"

    print(f"Found {len(manifests)} manifest files for orientation '{orientation}':")
    for manifest in manifests:
        file_size = manifest.stat().st_size / (1024 * 1024)  # MB
        line_count = sum(1 for _ in manifest.open('r', encoding='utf-8'))
        print(f"  - {manifest.name}: {line_count} entries ({file_size:.2f} MB)")

    print(f"\nMerging to: {output_file}")

    total_entries = 0
    total_errors = 0

    with output_file.open('w', encoding='utf-8') as outf:
        for manifest in manifests:
            with manifest.open('r', encoding='utf-8') as inf:
                for line_num, line in enumerate(inf, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # Verify JSON format if requested
                    if verify:
                        try:
                            json.loads(line)
                        except json.JSONDecodeError as e:
                            print(f"Warning: Invalid JSON in {manifest.name}:{line_num}: {e}")
                            total_errors += 1
                            continue

                    outf.write(line + '\n')
                    total_entries += 1

    print(f"\n✓ Merged {total_entries} entries to {output_file.name}")
    if total_errors > 0:
        print(f"⚠ Skipped {total_errors} invalid entries")

    return total_entries, total_errors


def merge_error_logs(directory: Path, orientation: str) -> int:
    """
    Merge all error log files for a given orientation.

    Args:
        directory: Directory containing error log files
        orientation: 'h' for horizontal, 'v' for vertical

    Returns:
        Total number of errors found
    """
    pattern = f"error_log_{orientation}_*.txt"
    error_logs = list(directory.glob(pattern))

    # Exclude the merged error log if it exists
    error_logs = [e for e in error_logs if e.name != f"error_log_{orientation}_all.txt"]

    if not error_logs:
        return 0

    output_file = directory / f"error_log_{orientation}_all.txt"

    print(f"\nMerging {len(error_logs)} error logs...")
    total_errors = 0

    with output_file.open('w', encoding='utf-8') as outf:
        for error_log in error_logs:
            if error_log.stat().st_size == 0:
                continue

            with error_log.open('r', encoding='utf-8') as inf:
                for line in inf:
                    outf.write(line)
                    total_errors += 1

    if total_errors > 0:
        print(f"✓ Merged {total_errors} error entries to {output_file.name}")
    else:
        print(f"✓ No errors found")

    return total_errors


def print_summary(directory: Path, orientation: str):
    """Print summary of merged data."""
    manifest_file = directory / f"manifest_{orientation}_all.jsonl"
    error_file = directory / f"error_log_{orientation}_all.txt"

    if not manifest_file.exists():
        return

    entry_count = sum(1 for _ in manifest_file.open('r', encoding='utf-8') if _.strip())
    manifest_size = manifest_file.stat().st_size / (1024 * 1024)  # MB

    error_count = 0
    if error_file.exists():
        error_count = sum(1 for _ in error_file.open('r', encoding='utf-8') if _.strip())

    # Calculate directory size
    dir_size = sum(f.stat().st_size for f in directory.glob('*.jpg')) / (1024 * 1024 * 1024)  # GB

    print(f"\n{'=' * 60}")
    print(f"Summary for {'Horizontal' if orientation == 'h' else 'Vertical'} ({orientation}):")
    print(f"  Directory:       {directory}")
    print(f"  Total entries:   {entry_count:,}")
    print(f"  Manifest size:   {manifest_size:.2f} MB")
    print(f"  Images size:     {dir_size:.2f} GB")
    if error_count > 0:
        print(f"  Errors:          {error_count}")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        description="Merge manifest files from batch processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge horizontal manifests
  python3 merge_manifests.py --dir output/ocr_out_h --orientation h

  # Merge vertical manifests
  python3 merge_manifests.py --dir output/ocr_out_v --orientation v

  # Merge both orientations
  python3 merge_manifests.py --dir output/ocr_out_h --orientation h
  python3 merge_manifests.py --dir output/ocr_out_v --orientation v

  # Or use the convenience option to merge both
  python3 merge_manifests.py --merge-both
        """
    )

    parser.add_argument(
        "--dir",
        type=str,
        help="Directory containing manifest files"
    )

    parser.add_argument(
        "--orientation",
        type=str,
        choices=['h', 'v'],
        help="Orientation: 'h' for horizontal, 'v' for vertical"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: manifest_{orientation}_all.jsonl in same directory)"
    )

    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip JSON verification (faster but may include invalid entries)"
    )

    parser.add_argument(
        "--merge-both",
        action="store_true",
        help="Merge both horizontal and vertical manifests (uses default paths)"
    )

    parser.add_argument(
        "--dir-h",
        type=str,
        default="output/ocr_out_h",
        help="Horizontal output directory (default: output/ocr_out_h)"
    )

    parser.add_argument(
        "--dir-v",
        type=str,
        default="output/ocr_out_v",
        help="Vertical output directory (default: output/ocr_out_v)"
    )

    args = parser.parse_args()

    verify = not args.no_verify

    # Merge both orientations
    if args.merge_both:
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║              Merging Both Orientations                         ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print()

        total_entries = 0
        total_errors = 0

        # Merge horizontal
        dir_h = Path(args.dir_h)
        if dir_h.exists():
            print(f"\n{'#' * 60}")
            print(f"# Merging HORIZONTAL manifests from {dir_h}")
            print(f"{'#' * 60}")
            entries, errors = merge_manifests(dir_h, 'h', verify=verify)
            merge_error_logs(dir_h, 'h')
            print_summary(dir_h, 'h')
            total_entries += entries
            total_errors += errors
        else:
            print(f"Warning: Directory {dir_h} does not exist, skipping horizontal merge")

        # Merge vertical
        dir_v = Path(args.dir_v)
        if dir_v.exists():
            print(f"\n{'#' * 60}")
            print(f"# Merging VERTICAL manifests from {dir_v}")
            print(f"{'#' * 60}")
            entries, errors = merge_manifests(dir_v, 'v', verify=verify)
            merge_error_logs(dir_v, 'v')
            print_summary(dir_v, 'v')
            total_entries += entries
            total_errors += errors
        else:
            print(f"Warning: Directory {dir_v} does not exist, skipping vertical merge")

        print(f"\n{'=' * 60}")
        print(f"TOTAL SUMMARY:")
        print(f"  Total entries:  {total_entries:,}")
        print(f"  Total errors:   {total_errors}")
        print(f"{'=' * 60}")
        print()
        print("Next steps:")
        print("  1. Convert to LMDB:")
        print(f"     python3 convert_to_lmdb.py --src {args.dir_h} --dst out_h.lmdb --verify")
        print(f"     python3 convert_to_lmdb.py --src {args.dir_v} --dst out_v.lmdb --verify")
        print()

        return

    # Single orientation merge
    if not args.dir or not args.orientation:
        parser.error("--dir and --orientation are required (or use --merge-both)")

    directory = Path(args.dir)
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        sys.exit(1)

    output_file = Path(args.output) if args.output else None

    print("╔════════════════════════════════════════════════════════════════╗")
    print("║                  Manifest Merger                               ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    # Merge manifests
    entries, errors = merge_manifests(directory, args.orientation, output_file, verify)

    # Merge error logs
    merge_error_logs(directory, args.orientation)

    # Print summary
    print_summary(directory, args.orientation)

    if entries == 0:
        print("\nNo entries merged. Check if manifest files exist in the directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()
