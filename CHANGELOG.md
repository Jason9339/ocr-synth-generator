# 更新日誌

## 2025-10-09 - 重大架構更新：LMDB 工作流程

### 🎯 核心改變

從「即時 NFS 同步」改為「全磁碟運行 + LMDB 封包」架構。

### ✅ 新增檔案

- `run_batch_local.sh` - 全磁碟運行主腳本
- `convert_to_lmdb.py` - LMDB 轉換工具
- `test_lmdb_workflow.sh` - 完整流程測試
- `LMDB_WORKFLOW.md` - 完整工作流程文檔
- `README_LMDB.md` - 快速參考指南

### 🗑️ 刪除檔案

舊版 NFS 同步相關檔案（已不需要）：

- `run_batch.sh` - 舊版 NFS 同步主腳本
- `test_preflight_check.sh` - 舊版 preflight 測試
- `test_small_batch.sh` - 舊版小批次測試
- `verify_local_disk.sh` - 舊版路徑驗證
- `BATCH_USAGE.md` - 舊版使用說明
- `FINAL_IMPROVEMENTS.md` - 舊版改進文檔
- `IMPROVEMENTS.md` - 舊版技術文檔
- `QUICK_START.md` - 舊版快速開始
- `README_BATCH.md` - 舊版批次說明

### 🔄 修改檔案

- `run_batch.py` - 移除遠端同步邏輯，簡化為純本機運行
- `README.md` - 更新為 LMDB 工作流程導向

### 📊 效能提升

| 指標 | 舊版（NFS 同步） | 新版（LMDB） | 改進 |
|------|-----------------|--------------|------|
| **NFS I/O 次數** | ~100 萬次 | 2 次 | **99.9998% ↓** |
| **傳輸時間** | 數小時 | 數分鐘 | **~50x ↑** |
| **訓練載入速度** | 慢（逐檔 open） | 快（LMDB） | **~10-50x ↑** |
| **管理難度** | 高（百萬檔案） | 低（2 檔案） | **顯著改善** |

### 🎓 新工作流程

```bash
# 1. 全磁碟生成
./run_batch_local.sh

# 2. 轉換 LMDB
python3 convert_to_lmdb.py --src /ocr_out_h --dst out_h.lmdb --verify
python3 convert_to_lmdb.py --src /ocr_out_v --dst out_v.lmdb --verify

# 3. 傳輸到 NFS（只傳 2 個檔案）
rsync -avh out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/

# 4. 清理本機
rm -rf /ocr_out_h /ocr_out_v
```

### 💡 升級建議

如果你之前使用舊版 NFS 同步方案：

1. **已生成的 JPG 資料**：可以手動轉換為 LMDB
   ```bash
   python3 convert_to_lmdb.py --src /mnt/whliao/out_h --dst out_h.lmdb
   ```

2. **新的生成任務**：直接使用新版流程
   ```bash
   ./run_batch_local.sh
   ```

3. **測試新流程**：先執行小規模測試
   ```bash
   ./test_lmdb_workflow.sh
   ```

### 📚 文檔更新

- 主要參考：[README_LMDB.md](README_LMDB.md)
- 詳細說明：[LMDB_WORKFLOW.md](LMDB_WORKFLOW.md)

### ⚠️ 注意事項

- 需要安裝 `lmdb` 套件：`pip install lmdb tqdm`
- 本機需至少 200GB 可用空間
- LMDB 格式不支援直接瀏覽 JPG（需透過程式讀取）

---

## 2025-10-07 - 批次處理優化

- 新增 `run_batch.py` - 支援大規模批次處理
- 新增多程序並行處理
- 改善記憶體管理

## 2025-09-19 - 專案初始化

- 建立 `synth.py` - 核心生成引擎
- 支援水平/垂直文字
- 自動字體 fallback 機制
