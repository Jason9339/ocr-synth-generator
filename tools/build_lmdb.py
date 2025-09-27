#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, io, lmdb, json, math
from pathlib import Path
from PIL import Image

def estimate_total_bytes(manifest_path: Path) -> int:
    est = 0
    with open(manifest_path, "r", encoding="utf-8") as f:
        for ln in f:
            j = json.loads(ln)
            p = Path(j["image_path"])
            if p.exists():
                est += p.stat().st_size + len(j["label"].encode("utf-8")) + 64
    return max(est, 1)

def build_lmdb(
    manifest: Path,
    lmdb_path: Path,
    map_size_bytes: int|None = None,
    shard_size: int|None = None
):
    lmdb_path.mkdir(parents=True, exist_ok=True)

    # 預估 map_size（給 1.5 倍緩衝）
    if map_size_bytes is None:
        total = estimate_total_bytes(manifest)
        map_size_bytes = int(total * 1.5)

    # 是否要分片
    shards = []
    with open(manifest, "r", encoding="utf-8") as f:
        records = [json.loads(x) for x in f]
    N = len(records)

    if shard_size and shard_size > 0 and N > shard_size:
        n_shards = math.ceil(N / shard_size)
        for s in range(n_shards):
            shards.append(records[s*shard_size:(s+1)*shard_size])
    else:
        shards = [records]

    global_index = 0
    for si, shard in enumerate(shards):
        subdir = lmdb_path / (f"shard_{si:03d}" if len(shards) > 1 else ".")
        if subdir.name != ".":
            subdir.mkdir(parents=True, exist_ok=True)

        env = lmdb.open(
            str(subdir if subdir.name != "." else lmdb_path),
            map_size=map_size_bytes,
            subdir=True,
            max_dbs=2,
            lock=True
        )
        db_img = env.open_db(b"images")
        db_lab = env.open_db(b"labels")

        with env.begin(write=True) as txn:
            for rec in shard:
                img_path = Path(rec["image_path"])
                label = rec["label"]
                if not img_path.exists():
                    print(f"[WARN] missing image: {img_path}")
                    continue
                key = f"{global_index:010d}".encode("ascii")
                # 直接讀二進位；若想重壓縮，可用 PIL 重新存 JPEG
                with open(img_path, "rb") as rf:
                    img_bytes = rf.read()
                txn.put(key, img_bytes, db=db_img)
                txn.put(key, label.encode("utf-8"), db=db_lab)
                global_index += 1
        env.sync()
        env.close()

    # 寫個簡單的 meta
    meta = {
        "num_samples": global_index,
        "sharded": len(shards) > 1,
        "shard_size": shard_size or 0
    }
    with open(lmdb_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Done. Wrote {global_index} samples into {lmdb_path} (shards={len(shards)}).")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=str, required=True)
    ap.add_argument("--lmdb_dir", type=str, required=True)
    ap.add_argument("--map_size_mb", type=int, default=0, help="預設 0=自動估算")
    ap.add_argument("--shard_size", type=int, default=0, help=">0 時啟用 LMDB 分片")
    args = ap.parse_args()

    manifest = Path(args.manifest)
    lmdb_dir = Path(args.lmdb_dir)
    map_size = args.map_size_mb * (1024**2) if args.map_size_mb > 0 else None
    shard_size = args.shard_size if args.shard_size > 0 else None

    build_lmdb(manifest, lmdb_dir, map_size_bytes=map_size, shard_size=shard_size)
