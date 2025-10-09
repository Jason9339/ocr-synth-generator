# OCR Synthesis Data Generator

高效能 OCR 訓練資料合成工具，支援繁體中文單行文字生成。

## 🚀 快速開始

請參閱 [README_LMDB.md](README_LMDB.md) 獲取完整使用說明。

### 3 步驟生成資料

```bash
# 1. 全磁碟生成
./run_batch_local.sh

# 2. 轉換 LMDB
python3 convert_to_lmdb.py --src /ocr_out_h --dst out_h.lmdb --verify
python3 convert_to_lmdb.py --src /ocr_out_v --dst out_v.lmdb --verify

# 3. 傳輸到遠端
rsync -avh out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/
```

## 📚 文檔

- **快速參考**: [README_LMDB.md](README_LMDB.md)
- **完整工作流程**: [LMDB_WORKFLOW.md](LMDB_WORKFLOW.md)

## ✨ 特色

- ✅ 全磁碟高速運行（避開 NFS 小檔 I/O 瓶頸）
- ✅ LMDB 格式輸出（訓練載入快速）
- ✅ 自動字體 fallback（確保 100% 可渲染）
- ✅ 多程序並行處理
- ✅ 支援水平/垂直文字