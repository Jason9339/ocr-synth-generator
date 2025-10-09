# OCR 合成資料生成器 - LMDB 工作流程

**推薦方案**：全磁碟運行 + LMDB 格式（避免 NFS 小檔地獄）

---

## 🚀 快速開始（3 步驟）

### 1. 全磁碟生成

```bash
# 安裝依賴（首次）
pip install lmdb tqdm

# 執行生成（全部在本機 /tmp）
./run_batch_local.sh
```

**完成後會產生**：
- `/ocr_out_h/` - 水平圖片 + manifest
- `/ocr_out_v/` - 垂直圖片 + manifest
- `report_YYYYMMDD_HHMMSS.json` - 統計報告

---

### 2. 轉換為 LMDB

```bash
# 轉換水平圖片（約 5-10 分鐘）
python3 convert_to_lmdb.py \
  --src /ocr_out_h \
  --dst out_h.lmdb \
  --verify

# 轉換垂直圖片
python3 convert_to_lmdb.py \
  --src /ocr_out_v \
  --dst out_v.lmdb \
  --verify
```

**結果**：得到 2 個 LMDB 檔案（每個約 16GB）

---

### 3. 傳輸到 NFS（只傳 2 個檔案！）

```bash
# 傳輸 LMDB（約 5-15 分鐘）
rsync -avh --progress out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/

# 清理本機暫存（可選）
rm -rf /ocr_out_h /ocr_out_v
```

---

## 📁 檔案結構

```
ocr-synth-generator/
├── synth.py                    # 圖片生成核心
├── run_batch.py                # 批次處理腳本
├── run_batch_local.sh          # ⭐ 主執行腳本（全磁碟運行）
├── convert_to_lmdb.py          # ⭐ LMDB 轉換工具
├── test_lmdb_workflow.sh       # 完整流程測試腳本
│
├── LMDB_WORKFLOW.md            # ⭐ 完整工作流程文檔
├── README_LMDB.md              # 快速參考（本檔案）
└── README.md                   # 專案說明
```

---

## 🎯 工作流程

```bash
./run_batch_local.sh              # 1. 生成到本機
python3 convert_to_lmdb.py ...   # 2. 轉 LMDB
rsync out_h.lmdb /mnt/...        # 3. 傳 2 個大檔
```

**優勢**：
- ✅ NFS 只傳 2 個檔案（快速穩定）
- ✅ 訓練載入快（LMDB 隨機存取）
- ✅ 備份管理簡單
- ✅ 避開 NFS 小檔 I/O 瓶頸

---

## ⚙️ 設定檔修改

### 本機輸出目錄

編輯 `run_batch_local.sh`：
```bash
# 預設：/tmp（通常是 tmpfs 或 overlay）
OUT_DIR_H="/ocr_out_h"
OUT_DIR_V="/ocr_out_v"

# 如果 /tmp 空間不足，可改用
OUT_DIR_H="/root/ocr_out_h"
OUT_DIR_V="/root/ocr_out_v"
```

### 生成參數

```bash
N_PER_LINE=20          # 每行生成 20 張圖
BATCH_SIZE=10000       # 每批 10000 行
NUM_WORKERS=6          # 6 個 CPU worker
SEED=20                # 隨機種子
```

---

## 📊 空間需求

| 階段 | 本機需求 | NFS 需求 |
|------|---------|----------|
| 生成 100 萬張圖 | ~80GB | 0 |
| 轉 LMDB | ~160GB（圖+LMDB） | 0 |
| 傳輸後 | 0（可清） | ~80GB（2 個 LMDB） |

**建議**：本機至少 **200GB 可用空間**

---

## 🔍 常見問題

### Q: 如何確認本機路徑不是 NFS？

```bash
./verify_local_disk.sh

# 或手動檢查
stat -f -c %T /tmp
# 預期：tmpfs, ext4, xfs, overlay（✅ 本機）
# 不該：nfs, cifs, smb（❌ 網路）
```

### Q: 本機空間不足怎麼辦？

```bash
# 選項 1: 減小 batch size
./run_batch_local.sh --batch_size 5000

# 選項 2: 分段執行
./run_batch_local.sh  # 執行一半
python3 convert_to_lmdb.py ...
rm -rf /tmp/ocr_out_*  # 清理
# 再執行另一半
```

### Q: 如何驗證 LMDB 正確性？

```bash
# 使用 --verify 選項
python3 convert_to_lmdb.py --src /ocr_out_h --dst test.lmdb --verify

# 或手動檢查
python3 -c "
import lmdb
env = lmdb.open('out_h.lmdb', readonly=True)
with env.begin() as txn:
    print('Sample count:', txn.stat()['entries'] // 2)
env.close()
"
```

---

## 📚 詳細文檔

- **完整工作流程**：[LMDB_WORKFLOW.md](LMDB_WORKFLOW.md)
- **技術改進說明**：[IMPROVEMENTS.md](IMPROVEMENTS.md)
- **舊版 NFS 同步方案**：[QUICK_START.md](QUICK_START.md)

---

## 🎓 訓練時使用 LMDB

```python
import lmdb
import io
from PIL import Image
from torch.utils.data import Dataset

class LMDBDataset(Dataset):
    def __init__(self, lmdb_path):
        self.env = lmdb.open(str(lmdb_path), readonly=True, lock=False)
        with self.env.begin() as txn:
            metadata = json.loads(txn.get(b'__metadata__'))
            self.length = metadata['num_samples']

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        with self.env.begin() as txn:
            img_key = f'image-{idx:08d}'.encode()
            label_key = f'label-{idx:08d}'.encode()

            img_bytes = txn.get(img_key)
            label = txn.get(label_key).decode('utf-8')

            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            return img, label

# 使用
dataset = LMDBDataset('out_h.lmdb')
loader = DataLoader(dataset, batch_size=32, shuffle=True)
```

---

## ✅ 檢查清單

執行前確認：
- [ ] 本機至少 200GB 可用空間（`df -h /tmp`）
- [ ] 已安裝 lmdb 套件（`pip install lmdb tqdm`）
- [ ] 確認輸出路徑是本機檔案系統（`./verify_local_disk.sh`）

執行後確認：
- [ ] 報告檔案已產生（`report_*.json`）
- [ ] LMDB 檔案大小合理（約 80KB/張圖）
- [ ] 已成功傳輸到 NFS（`ls -lh /mnt/whliao/lmdb/`）
- [ ] （可選）已清理本機暫存

---

## 🎉 總結

**新版流程**：生成 → 轉 LMDB → 傳 2 個檔案

**優勢**：快速、穩定、易管理、訓練快

**推薦指數**：⭐⭐⭐⭐⭐（除非有特殊需求，否則一律用這個！）
