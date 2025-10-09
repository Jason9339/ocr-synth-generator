# 全新工作流程：全磁碟運行 + LMDB 格式

## 🎯 新架構概覽

```
┌─────────────────────────────────────────────────────────────┐
│ 階段 1: 全磁碟生成（本機 SSD）                              │
├─────────────────────────────────────────────────────────────┤
│ lines.txt → [synth.py] → JPG + manifest                    │
│                  ↓                                          │
│           /ocr_out_h  (本機暫存)                        │
│           /ocr_out_v  (本機暫存)                        │
│                  ↓                                          │
│           report_YYYYMMDD_HHMMSS.json (統計報告)           │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 階段 2: 轉換 LMDB（本機）                                   │
├─────────────────────────────────────────────────────────────┤
│ [convert_to_lmdb.py]                                        │
│     /ocr_out_h → out_h.lmdb (單一檔案)                  │
│     /ocr_out_v → out_v.lmdb (單一檔案)                  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 階段 3: 傳輸到 NFS（只傳兩個檔案）                          │
├─────────────────────────────────────────────────────────────┤
│ rsync -a out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/           │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ 優勢對比

| 項目 | 舊版（NFS 同步） | 新版（LMDB） |
|------|-----------------|--------------|
| **NFS I/O** | 高（百萬次小檔寫入） | **極低（只傳 2 個大檔）** ✅ |
| **本機空間** | 16GB/batch（立即清） | 全部暫存（~80GB）→ 完成後清 |
| **傳輸效率** | 慢（大量小檔） | **快（單一大檔）** ✅ |
| **可靠性** | 中（中途中斷易爛） | **高（一次完成再封包）** ✅ |
| **訓練讀取** | 慢（需 open 百萬次） | **快（LMDB 隨機存取）** ✅ |
| **備份管理** | 難（巨量小檔） | **易（只有 2 個檔案）** ✅ |

---

## 🚀 完整操作流程

### Step 1: 全磁碟生成

```bash
# 執行本機運行版本（不同步 NFS）
./run_batch_local.sh

# 或自訂參數
./run_batch_local.sh \
  --out_dir_h /ocr_out_h \
  --out_dir_v /ocr_out_v \
  --batch_size 10000 \
  --num_workers 6
```

**執行完成後會自動產生**：
- `/ocr_out_h/` - 水平圖片 + manifest
- `/ocr_out_v/` - 垂直圖片 + manifest
- `report_YYYYMMDD_HHMMSS.json` - 統計報告

**報告範例**：
```json
{
  "timestamp": "2025-10-09T12:34:56+08:00",
  "duration_seconds": 3600,
  "duration_human": "1h 0m 0s",
  "output": {
    "horizontal": {
      "image_count": 200000,
      "size": "16G",
      "errors": 0
    },
    "vertical": {
      "image_count": 200000,
      "size": "16G",
      "errors": 0
    },
    "total_images": 400000
  }
}
```

---

### Step 2: 轉換為 LMDB

```bash
# 安裝 lmdb（如果還沒裝）
pip install lmdb tqdm

# 轉換水平圖片
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

**輸出範例**：
```
Reading manifest: /ocr_out_h/manifest_h_all.jsonl
Found 200000 entries in manifest
Creating LMDB: out_h.lmdb
  Estimated size: 19531.2 MB
Writing to LMDB: 100%|██████████| 200000/200000 [02:15<00:00, 1479.23it/s]

✓ LMDB created successfully!
  Entries: 200000
  Size: 16384.5 MB
  Location: /home/jason/ocr-synth-generator/out_h.lmdb
```

---

### Step 3: 傳輸到 NFS（只傳 2 個大檔）

```bash
# 創建 NFS 目標目錄
mkdir -p /mnt/whliao/lmdb

# 傳輸 LMDB 檔案（只有 2 個檔案！）
rsync -avh --progress out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/

# 或使用 scp（如果是遠端）
scp out_h.lmdb out_v.lmdb user@nas:/mnt/whliao/lmdb/
```

**傳輸速度對比**：
- 舊版（百萬個 .jpg）：數小時，容易中斷
- 新版（2 個 .lmdb）：數分鐘，穩定快速 ✅

---

### Step 4: （可選）清理本機暫存

```bash
# 確認 LMDB 已成功傳輸後
ls -lh /mnt/whliao/lmdb/

# 清理本機圖片（釋放空間）
rm -rf /ocr_out_h /ocr_out_v
```

---

## 📊 空間需求估算

假設生成 **100 萬張圖片**（50 萬水平 + 50 萬垂直）：

| 階段 | 本機空間 | NFS 空間 |
|------|---------|----------|
| 生成中 | ~80GB（全部圖片） | 0 |
| 轉 LMDB | ~160GB（圖片 + LMDB） | 0 |
| 傳輸後 | 0（可清理） | ~80GB（2 個 LMDB） |

**關鍵**：本機需至少 **200GB 可用空間**（含安全邊際）

---

## 🔍 驗證 LMDB

### 快速驗證
```bash
python3 convert_to_lmdb.py --src /ocr_out_h --dst test.lmdb --verify
```

### 手動驗證（Python）
```python
import lmdb
import json

env = lmdb.open('out_h.lmdb', readonly=True)

with env.begin() as txn:
    # 讀取 metadata
    metadata = json.loads(txn.get(b'__metadata__'))
    print(f"Total samples: {metadata['num_samples']}")

    # 讀取第一筆資料
    img_bytes = txn.get(b'image-00000000')
    label_bytes = txn.get(b'label-00000000')

    print(f"Image size: {len(img_bytes)} bytes")
    print(f"Label: {label_bytes.decode('utf-8')}")

env.close()
```

---

## 🎓 訓練時如何使用 LMDB

### PyTorch Dataset 範例

```python
import lmdb
import io
from PIL import Image
from torch.utils.data import Dataset

class LMDBDataset(Dataset):
    def __init__(self, lmdb_path, transform=None):
        self.env = lmdb.open(str(lmdb_path), readonly=True, lock=False)
        with self.env.begin() as txn:
            metadata = json.loads(txn.get(b'__metadata__'))
            self.length = metadata['num_samples']
        self.transform = transform

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        with self.env.begin() as txn:
            img_key = f'image-{idx:08d}'.encode()
            label_key = f'label-{idx:08d}'.encode()

            img_bytes = txn.get(img_key)
            label_bytes = txn.get(label_key)

            # Decode image
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            label = label_bytes.decode('utf-8')

            if self.transform:
                img = self.transform(img)

            return img, label

# 使用
dataset = LMDBDataset('out_h.lmdb', transform=transforms.ToTensor())
loader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=4)
```

---

## ⚙️ 參數調整建議

### 本機空間不足時

```bash
# 減小 batch_size（降低峰值佔用）
./run_batch_local.sh --batch_size 5000

# 或分段執行
./run_batch_local.sh --batch_size 10000  # 生成一半
python3 convert_to_lmdb.py ...           # 立即轉 LMDB
rm -rf /tmp/ocr_out_*                   # 清理
# 再執行另一半...
```

### 加速生成

```bash
# 增加 worker 數量
./run_batch_local.sh --num_workers 12

# 減少每行圖片數（測試用）
./run_batch_local.sh --n_per_line 10
```

---

## 🛠️ 故障排查

### Q: LMDB 轉換時記憶體不足

```bash
# 檢查記憶體使用
free -h

# 減少處理批次（目前是一次全部載入）
# 如果遇到問題，可以改寫 convert_to_lmdb.py 使用分批寫入
```

### Q: 本機空間不夠

```bash
# 檢查可用空間
df -h /tmp

# 選項 1: 使用其他本機路徑
./run_batch_local.sh --out_dir_h /root/ocr_out_h

# 選項 2: 分段生成（見上方參數調整）
```

### Q: LMDB 檔案過大

```bash
# 檢查單個 LMDB 大小
du -h out_h.lmdb

# 如果超過 100GB，建議分成多個 LMDB
# 修改腳本支援多個輸出檔案
```

---

## 📝 完整工作流程範例

```bash
# ========================================
# 完整流程（100 萬張圖範例）
# ========================================

# 1. 執行生成（約 1-2 小時）
./run_batch_local.sh

# 2. 檢查報告
cat report_*.json

# 3. 轉換 LMDB（約 5-10 分鐘）
python3 convert_to_lmdb.py --src /ocr_out_h --dst out_h.lmdb --verify
python3 convert_to_lmdb.py --src /ocr_out_v --dst out_v.lmdb --verify

# 4. 傳輸到 NFS（約 5-15 分鐘）
rsync -avh --progress out_h.lmdb out_v.lmdb /mnt/whliao/lmdb/

# 5. 驗證傳輸成功
ls -lh /mnt/whliao/lmdb/

# 6. 清理本機（釋放 ~160GB）
rm -rf /ocr_out_h /ocr_out_v
```

---

## 🎉 總結

### 為什麼這個方案更好？

1. **NFS 友善**：只傳 2 個大檔，避開小檔 I/O 地獄
2. **本機高效**：生成時 100% SSD 速度
3. **訓練快速**：LMDB 隨機存取比 open() 百萬次快得多
4. **容易管理**：備份/傳輸/刪除只需處理 2 個檔案
5. **可靠穩定**：一次完成再封包，中途中斷損失小

### 與舊版對比

| 操作 | 舊版 | 新版 |
|------|------|------|
| 生成 100 萬張圖 | 分批同步 NFS，慢 | 全本機，快 ✅ |
| 傳輸到 NFS | 數小時，易中斷 | 數分鐘，穩定 ✅ |
| 訓練載入 | 慢（需 open 百萬次） | 快（LMDB） ✅ |
| 備份 | 難（巨量小檔） | 易（2 個大檔） ✅ |

**建議**：除非有特殊需求（如需要直接存取 JPG），否則一律使用 LMDB 方案！
