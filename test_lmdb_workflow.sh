#!/bin/bash
# 測試 LMDB 工作流程（小規模完整測試）

set -euo pipefail

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           LMDB 工作流程測試（50 行 → 100 張圖）               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 測試配置
TEST_OUT_H="/tmp/test_ocr_h"
TEST_OUT_V="/tmp/test_ocr_v"
TEST_LMDB_H="test_out_h.lmdb"
TEST_LMDB_V="test_out_v.lmdb"

# 清理舊測試資料
echo "清理舊測試資料..."
rm -rf "$TEST_OUT_H" "$TEST_OUT_V" "$TEST_LMDB_H" "$TEST_LMDB_V"

# ============================================================
# 階段 1: 生成測試資料（只處理前 50 行）
# ============================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "階段 1: 生成測試資料（水平 + 垂直，各 100 張）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 檢查必要檔案
if [ ! -f "lines.txt" ]; then
    echo "[ERROR] lines.txt not found"
    exit 1
fi

# 生成水平測試資料
echo "1/2 生成水平測試資料..."
if ! python3 run_batch.py \
    --lines lines.txt \
    --fonts_dir fonts \
    --bgs_dir backgrounds \
    --out_dir "$TEST_OUT_H" \
    --n_per_line 2 \
    --box_jitter "2,2" \
    --last_resort_font "NotoSansTC-Regular.ttf" \
    --seed 42 \
    --num_workers 2 \
    --batch_size 25
then
    echo "[ERROR] 水平資料生成失敗"
    exit 1
fi

# 生成垂直測試資料
echo ""
echo "2/2 生成垂直測試資料..."
if ! python3 run_batch.py \
    --lines lines.txt \
    --fonts_dir fonts \
    --bgs_dir backgrounds \
    --out_dir "$TEST_OUT_V" \
    --n_per_line 2 \
    --vertical \
    --box_jitter "2,2" \
    --last_resort_font "NotoSansTC-Regular.ttf" \
    --seed 42 \
    --num_workers 2 \
    --batch_size 25
then
    echo "[ERROR] 垂直資料生成失敗"
    exit 1
fi

echo ""
echo "✓ 階段 1 完成"

# ============================================================
# 階段 2: 合併 manifest
# ============================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "階段 2: 合併 manifest"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cat "$TEST_OUT_H"/manifest_h_*.jsonl > "$TEST_OUT_H/manifest_h_all.jsonl"
cat "$TEST_OUT_V"/manifest_v_*.jsonl > "$TEST_OUT_V/manifest_v_all.jsonl"

H_COUNT=$(wc -l < "$TEST_OUT_H/manifest_h_all.jsonl")
V_COUNT=$(wc -l < "$TEST_OUT_V/manifest_v_all.jsonl")

echo "水平 manifest: $H_COUNT 筆"
echo "垂直 manifest: $V_COUNT 筆"
echo ""
echo "✓ 階段 2 完成"

# ============================================================
# 階段 3: 轉換為 LMDB
# ============================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "階段 3: 轉換為 LMDB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 檢查是否已安裝 lmdb
if ! python3 -c "import lmdb" 2>/dev/null; then
    echo "[ERROR] lmdb 套件未安裝"
    echo "請執行: pip install lmdb tqdm"
    exit 1
fi

echo "1/2 轉換水平資料..."
if ! python3 convert_to_lmdb.py \
    --src "$TEST_OUT_H" \
    --dst "$TEST_LMDB_H" \
    --verify
then
    echo "[ERROR] 水平 LMDB 轉換失敗"
    exit 1
fi

echo ""
echo "2/2 轉換垂直資料..."
if ! python3 convert_to_lmdb.py \
    --src "$TEST_OUT_V" \
    --dst "$TEST_LMDB_V" \
    --verify
then
    echo "[ERROR] 垂直 LMDB 轉換失敗"
    exit 1
fi

echo ""
echo "✓ 階段 3 完成"

# ============================================================
# 驗證結果
# ============================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "驗證結果"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 檢查檔案大小
H_LMDB_SIZE=$(du -h "$TEST_LMDB_H" | cut -f1)
V_LMDB_SIZE=$(du -h "$TEST_LMDB_V" | cut -f1)

echo "1. LMDB 檔案大小："
echo "   水平: $H_LMDB_SIZE"
echo "   垂直: $V_LMDB_SIZE"
echo ""

echo "2. LMDB 檔案位置："
echo "   $(pwd)/$TEST_LMDB_H"
echo "   $(pwd)/$TEST_LMDB_V"
echo ""

# 簡單的 Python 驗證
echo "3. 驗證 LMDB 內容："
python3 << 'EOF'
import lmdb
import json

def verify_lmdb(path):
    env = lmdb.open(path, readonly=True)
    with env.begin() as txn:
        metadata = json.loads(txn.get(b'__metadata__'))
        print(f"   {path}: {metadata['num_samples']} 筆資料")

        # 測試讀取第一筆
        img_bytes = txn.get(b'image-00000000')
        label_bytes = txn.get(b'label-00000000')
        if img_bytes and label_bytes:
            print(f"   ✓ 可正常讀取（圖片: {len(img_bytes)} bytes, 標籤: {label_bytes.decode('utf-8')[:20]}...）")
    env.close()

verify_lmdb('test_out_h.lmdb')
verify_lmdb('test_out_v.lmdb')
EOF

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                      測試全部通過！✓                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "下一步："
echo "  1. 執行正式生成:"
echo "     ./run_batch_local.sh"
echo ""
echo "  2. 清理測試資料:"
echo "     rm -rf $TEST_OUT_H $TEST_OUT_V $TEST_LMDB_H $TEST_LMDB_V"
echo ""
