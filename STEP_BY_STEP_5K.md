# 分批執行指南（5000行/批次）

針對 34,413 行資料的完整執行步驟。

---

## 批次劃分

共 14 個批次（7 水平 + 7 垂直）

| 批次 | 起始行 | 結束行 | 行數 | 圖片數 | 大小 |
|------|--------|--------|------|--------|------|
| 1-6 | 0-30000 | 5000間隔 | 5,000 | 100,000 | ~7.6GB |
| 7 | 30000-34413 | - | 4,413 | 88,260 | ~6.7GB |

**每個方向總計**: 688,260張，~52.5GB
**兩方向總計**: 1,376,520張，~105GB

---

## 第一階段：水平方向（7批次）

```bash
./run_single_batch.sh 0 5000 h
./run_single_batch.sh 5000 10000 h
./run_single_batch.sh 10000 15000 h
./run_single_batch.sh 15000 20000 h
./run_single_batch.sh 20000 25000 h
./run_single_batch.sh 25000 30000 h
./run_single_batch.sh 30000 34413 h
```

**檢查點**：
```bash
# 檢查 manifest 檔案
ls -lh output/ocr_out_h/manifest_h_*.jsonl

# 應該看到 7 個檔案
ls output/ocr_out_h/manifest_h_*.jsonl | wc -l

# 檢查目錄大小
du -sh output/ocr_out_h
```

---

## 第二階段：垂直方向（7批次）

```bash
./run_single_batch.sh 0 5000 v
./run_single_batch.sh 5000 10000 v
./run_single_batch.sh 10000 15000 v
./run_single_batch.sh 15000 20000 v
./run_single_batch.sh 20000 25000 v
./run_single_batch.sh 25000 30000 v
./run_single_batch.sh 30000 34413 v
```

**檢查點**：
```bash
# 檢查 manifest 檔案
ls -lh output/ocr_out_v/manifest_v_*.jsonl

# 應該看到 7 個檔案
ls output/ocr_out_v/manifest_v_*.jsonl | wc -l

# 檢查目錄大小
du -sh output/ocr_out_v
```

---

## 第三階段：合併 Manifest

```bash
python3 merge_manifests.py --merge-both
```

**預期輸出**：
```
Found 7 manifest files for orientation 'h'
✓ Merged 688260 entries to manifest_h_all.jsonl

Found 7 manifest files for orientation 'v'
✓ Merged 688260 entries to manifest_v_all.jsonl

TOTAL SUMMARY:
  Total entries:  1,376,520
```

**驗證**：
```bash
# 檢查合併後的 manifest
wc -l output/ocr_out_h/manifest_h_all.jsonl
wc -l output/ocr_out_v/manifest_v_all.jsonl
# 預期：各 688,260 行
```

---

## 第四階段：轉換 LMDB

### 轉換水平
```bash
python3 convert_to_lmdb.py \
  --src output/ocr_out_h \
  --dst out_h.lmdb \
  --verify
```

### 轉換垂直
```bash
python3 convert_to_lmdb.py \
  --src output/ocr_out_v \
  --dst out_v.lmdb \
  --verify
```

**驗證**：
```bash
ls -lh out_h.lmdb out_v.lmdb

# 快速檢查
python3 << 'EOF'
import lmdb
import json

for name in ['out_h.lmdb', 'out_v.lmdb']:
    env = lmdb.open(name, readonly=True)
    with env.begin() as txn:
        metadata = json.loads(txn.get(b'__metadata__'))
        print(f"{name}: {metadata['num_samples']:,} samples")
    env.close()
EOF
```

**預期**：各 688,260 samples

---

## 第五階段：傳輸（可選）

如需傳輸到 NFS：

```bash
rsync -avh --progress out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/
```

---

## 第六階段：清理（可選）

```bash
# 確認 LMDB 正確後
rm -rf output/ocr_out_h output/ocr_out_v
```

**釋放空間**: ~105 GB

---

## 檢查點快速參考

### 檢查磁碟空間
```bash
df -h .
du -sh output/ocr_out_h output/ocr_out_v
```

### 檢查批次進度
```bash
# 水平方向
ls output/ocr_out_h/manifest_h_*.jsonl | wc -l

# 垂直方向
ls output/ocr_out_v/manifest_v_*.jsonl | wc -l
```

### 檢查圖片數量
```bash
find output/ocr_out_h -name "*.jpg" | wc -l
find output/ocr_out_v -name "*.jpg" | wc -l
```

### 檢查條目數
```bash
cat output/ocr_out_h/manifest_h_*.jsonl | wc -l
cat output/ocr_out_v/manifest_v_*.jsonl | wc -l
```

---

## 故障處理

### 批次被中斷
直接重新執行該批次：
```bash
./run_single_batch.sh <start> <end> <h/v>
```

### 磁碟空間不足
檢查並清理：
```bash
df -h .
du -sh output/ocr_out_*
```

### 檢查某批次是否完成
```bash
ls -lh output/ocr_out_h/manifest_h_0_5000.jsonl
wc -l output/ocr_out_h/manifest_h_0_5000.jsonl
# 預期：約 100,000 行
```

---

## 預估時間

- 每批次（5000行）：2-5 小時
- 水平 7 批次：14-35 小時
- 垂直 7 批次：14-35 小時
- 合併：1-2 分鐘
- LMDB 轉換：10-20 分鐘
- **總計**：28-70 小時

---

## 執行清單

```
準備：
☐ 檢查磁碟空間 (df -h .)
☐ 安裝依賴 (pip install lmdb tqdm)

水平方向：
☐ ./run_single_batch.sh 0 5000 h
☐ ./run_single_batch.sh 5000 10000 h
☐ ./run_single_batch.sh 10000 15000 h
☐ ./run_single_batch.sh 15000 20000 h
☐ ./run_single_batch.sh 20000 25000 h
☐ ./run_single_batch.sh 25000 30000 h
☐ ./run_single_batch.sh 30000 34413 h

垂直方向：
☐ ./run_single_batch.sh 0 5000 v
☐ ./run_single_batch.sh 5000 10000 v
☐ ./run_single_batch.sh 10000 15000 v
☐ ./run_single_batch.sh 15000 20000 v
☐ ./run_single_batch.sh 20000 25000 v
☐ ./run_single_batch.sh 25000 30000 v
☐ ./run_single_batch.sh 30000 34413 v

後續處理：
☐ python3 merge_manifests.py --merge-both
☐ python3 convert_to_lmdb.py --src output/ocr_out_h --dst out_h.lmdb --verify
☐ python3 convert_to_lmdb.py --src output/ocr_out_v --dst out_v.lmdb --verify
☐ (可選) rsync 傳輸到 NFS
☐ (可選) rm -rf output/ocr_out_h output/ocr_out_v

完成！
```
