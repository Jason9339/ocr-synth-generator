#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, lmdb
from pathlib import Path

def find_last_key(env, db):
    # 掠過去找到最後一個 key
    with env.begin() as txn:
        cur = txn.cursor(db=db)
        if cur.last():
            return int(cur.key().decode("ascii"))
    return -1

def append_from_manifest(lmdb_dir: Path, manifest: Path, map_size_mb: int = 0):
    lmdb_dir = Path(lmdb_dir)
    target = lmdb_dir if (lmdb_dir / "data.mdb").exists() else (lmdb_dir / "shard_000")
    target.mkdir(parents=True, exist_ok=True)

    env = lmdb.open(str(target), map_size=(map_size_mb*(1024**2) if map_size_mb>0 else 1<<40),
                    max_dbs=2, subdir=True, lock=True)
    db_img = env.open_db(b"images")
    db_lab = env.open_db(b"labels")

    last = find_last_key(env, db_img)
    next_idx = last + 1

    added = 0
    with open(manifest, "r", encoding="utf-8") as f, env.begin(write=True) as txn:
        for ln in f:
            rec = json.loads(ln)
            p = Path(rec["image_path"])
            if not p.exists():
                print(f"[WARN] missing {p}")
                continue
            k = f"{next_idx:010d}".encode("ascii")
            with open(p, "rb") as rf:
                img_bytes = rf.read()
            txn.put(k, img_bytes, db=db_img)
            txn.put(k, rec["label"].encode("utf-8"), db=db_lab)
            next_idx += 1; added += 1

    env.sync(); env.close()
    print(f"Appended {added} samples into {target}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--lmdb_dir", type=str, required=True)
    ap.add_argument("--manifest", type=str, required=True)
    ap.add_argument("--map_size_mb", type=int, default=0)
    args = ap.parse_args()
    append_from_manifest(Path(args.lmdb_dir), Path(args.manifest), args.map_size_mb)
