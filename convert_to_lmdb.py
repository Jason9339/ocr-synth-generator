#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert OCR synthesis output (JPG + manifest) to LMDB format.
This avoids having millions of small files on NFS.
"""

import argparse
import json
import lmdb
from pathlib import Path
from tqdm import tqdm


def convert_to_lmdb(src_dir: Path, dst_lmdb: Path, manifest_file: str = None):
    """
    Convert directory of images + manifest to LMDB.

    Args:
        src_dir: Source directory containing images and manifest files
        dst_lmdb: Output LMDB file path
        manifest_file: Specific manifest file to use (default: manifest_*_all.jsonl)
    """
    # Find manifest file
    if manifest_file:
        manifest_path = src_dir / manifest_file
    else:
        # Auto-detect merged manifest
        candidates = list(src_dir.glob("manifest_*_all.jsonl"))
        if not candidates:
            raise FileNotFoundError(f"No manifest_*_all.jsonl found in {src_dir}")
        manifest_path = candidates[0]

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    print(f"Reading manifest: {manifest_path}")

    # Read all entries
    entries = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    print(f"Found {len(entries)} entries in manifest")

    # Calculate LMDB size (images are ~80KB each, add 20% buffer)
    map_size = len(entries) * 100 * 1024  # 100KB per entry with buffer

    print(f"Creating LMDB: {dst_lmdb}")
    print(f"  Estimated size: {map_size / 1024 / 1024:.1f} MB")

    # Create LMDB
    env = lmdb.open(
        str(dst_lmdb),
        map_size=map_size,
        readonly=False,
        meminit=False,
        map_async=True,
    )

    # Write entries
    with env.begin(write=True) as txn:
        for idx, entry in enumerate(tqdm(entries, desc="Writing to LMDB")):
            # Read image
            img_path = Path(entry["image_path"])
            if not img_path.exists():
                print(f"[WARN] Image not found: {img_path}, skipping")
                continue

            with open(img_path, "rb") as img_file:
                img_bytes = img_file.read()

            # Store in LMDB
            # Key format: image-{idx:08d}
            img_key = f"image-{idx:08d}".encode()
            label_key = f"label-{idx:08d}".encode()

            txn.put(img_key, img_bytes)
            txn.put(label_key, entry["label"].encode("utf-8"))

        # Store metadata
        metadata = {
            "num_samples": len(entries),
            "manifest": str(manifest_path.name),
        }
        txn.put(b"__metadata__", json.dumps(metadata).encode("utf-8"))

    env.close()

    # Verify
    actual_size = dst_lmdb.stat().st_size if dst_lmdb.is_file() else sum(
        f.stat().st_size for f in dst_lmdb.iterdir()
    )
    print(f"\n✓ LMDB created successfully!")
    print(f"  Entries: {len(entries)}")
    print(f"  Size: {actual_size / 1024 / 1024:.1f} MB")
    print(f"  Location: {dst_lmdb.resolve()}")


def verify_lmdb(lmdb_path: Path, num_samples: int = 5):
    """Verify LMDB by reading a few samples."""
    print(f"\nVerifying LMDB: {lmdb_path}")

    env = lmdb.open(str(lmdb_path), readonly=True)

    with env.begin() as txn:
        # Read metadata
        metadata_bytes = txn.get(b"__metadata__")
        if metadata_bytes:
            metadata = json.loads(metadata_bytes.decode("utf-8"))
            print(f"  Metadata: {metadata}")

        # Sample a few entries
        print(f"\n  Sampling {num_samples} entries:")
        for i in range(min(num_samples, metadata.get("num_samples", 0))):
            img_key = f"image-{i:08d}".encode()
            label_key = f"label-{i:08d}".encode()

            img_bytes = txn.get(img_key)
            label_bytes = txn.get(label_key)

            if img_bytes and label_bytes:
                label = label_bytes.decode("utf-8")
                print(f"    [{i:08d}] Label: {label[:50]}... | Image size: {len(img_bytes)} bytes")

    env.close()
    print("\n✓ Verification complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Convert OCR synthesis output to LMDB format"
    )
    parser.add_argument(
        "--src",
        type=str,
        required=True,
        help="Source directory containing images and manifest",
    )
    parser.add_argument(
        "--dst",
        type=str,
        required=True,
        help="Destination LMDB file path (e.g., out_h.lmdb)",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Specific manifest file to use (default: auto-detect manifest_*_all.jsonl)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify LMDB after creation",
    )
    args = parser.parse_args()

    src_dir = Path(args.src)
    dst_lmdb = Path(args.dst)

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        return 1

    if dst_lmdb.exists():
        print(f"Error: Destination already exists: {dst_lmdb}")
        print("Please remove it first or choose a different name.")
        return 1

    # Convert
    convert_to_lmdb(src_dir, dst_lmdb, args.manifest)

    # Verify if requested
    if args.verify:
        verify_lmdb(dst_lmdb)

    return 0


if __name__ == "__main__":
    exit(main())
