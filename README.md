# OCR Synthesis Data Generator

高效能 OCR 訓練資料合成工具，支援繁體中文單行文字生成。

---

## 🚀 快速執行

針對 34,413 行資料，每批次 5000 行的執行流程。

### 第一階段：生成圖片（水平方向）

```bash
./run_single_batch.sh 0 5000 h
./run_single_batch.sh 5000 10000 h
./run_single_batch.sh 10000 15000 h
./run_single_batch.sh 15000 20000 h
./run_single_batch.sh 20000 25000 h
./run_single_batch.sh 25000 30000 h
./run_single_batch.sh 30000 34413 h
```

### 第二階段：生成圖片（垂直方向）

```bash
./run_single_batch.sh 0 5000 v
./run_single_batch.sh 5000 10000 v
./run_single_batch.sh 10000 15000 v
./run_single_batch.sh 15000 20000 v
./run_single_batch.sh 20000 25000 v
./run_single_batch.sh 25000 30000 v
./run_single_batch.sh 30000 34413 v
```

### 第三階段：合併 Manifest

```bash
python3 merge_manifests.py --merge-both
```

### 第四階段：轉換 LMDB

```bash
python3 convert_to_lmdb.py --src output/ocr_out_h --dst out_h.lmdb --verify
python3 convert_to_lmdb.py --src output/ocr_out_v --dst out_v.lmdb --verify
```

### 第五階段：傳輸到 NFS

```bash
rsync -avh --progress out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/
```

### 第六階段：清理（可選）

```bash
# 確認傳輸成功後
rm -rf output/ocr_out_h output/ocr_out_v
```

---

## 📚 詳細文檔

- **完整分步指南**: [STEP_BY_STEP_5K.md](STEP_BY_STEP_5K.md) - 每個批次的詳細檢查點和預期結果
- **批次規劃工具**: `python3 plan_batches.py --batch-size 5000`

---

## 🛠️ 工具說明

### run_single_batch.sh
執行單個批次的圖片生成。

語法：`./run_single_batch.sh <起始行> <結束行> <方向>`
- 方向：`h` (水平) 或 `v` (垂直)

### merge_manifests.py
合併所有批次的 manifest 檔案。

語法：`python3 merge_manifests.py --merge-both`

### convert_to_lmdb.py
將圖片和 manifest 轉換為 LMDB 格式。

語法：`python3 convert_to_lmdb.py --src <目錄> --dst <輸出.lmdb> --verify`

### plan_batches.py
規劃批次執行計劃。

語法：`python3 plan_batches.py --batch-size <行數>`

---

## 📊 資源需求

- **總圖片數**: ~1,376,520 張（水平 + 垂直）
- **磁碟空間**: ~105 GB
- **建議批次大小**: 5,000 行（每批次 ~2-5 小時）
- **總執行時間**: ~28-70 小時（14 個批次）

---

## 📁 輸出目錄結構

```
/mnt/whliao/
├── ocr_out_h/              # 水平方向輸出
│   ├── *.jpg               # 圖片檔案
│   ├── manifest_h_*.jsonl  # 各批次 manifest
│   └── manifest_h_all.jsonl # 合併後的 manifest
├── ocr_out_v/              # 垂直方向輸出
│   ├── *.jpg
│   ├── manifest_v_*.jsonl
│   └── manifest_v_all.jsonl
└── lmdb/                   # 最終 LMDB 輸出
    ├── out_h.lmdb/
    └── out_v.lmdb/
```

---

## ⚠️ 注意事項

1. **批次被中斷**：直接重新執行該批次即可
2. **檢查進度**：`ls -lh output/ocr_out_h/manifest_h_*.jsonl`
3. **磁碟空間**：`df -h .`
4. **每批次需逐個執行**，等待上一批次完成後再執行下一個

---

## ✨ 特色

- ✅ 避免 CPU 時間限制（分批執行）
- ✅ 批次失敗可單獨重試
- ✅ 自動字體 fallback（確保 100% 可渲染）
- ✅ 多程序並行處理
- ✅ LMDB 格式輸出（訓練載入快速）
- ✅ 支援水平/垂直文字
