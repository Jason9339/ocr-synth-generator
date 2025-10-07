# 批次處理使用說明

## 更新內容

### synth.py 新增參數

- `--start_line`: 起始行號（從 0 開始）
- `--end_line`: 結束行號（不含），None 表示到結尾
- `--num_workers`: CPU worker 數量（已存在但用於批次腳本參考）

## 使用方法

### ⭐ 方法 1: 一鍵執行全部（最簡單！推薦）

**新的 run_batch.sh 現在會自動執行水平和垂直兩種生成！**

#### 使用預設配置（最簡單）

```bash
./run_batch.sh
```

就這麼簡單！腳本會：
1. ✅ 顯示配置和預估資訊（總圖片數、磁碟空間需求等）
2. ✅ 詢問是否繼續
3. ✅ 自動執行水平文字生成（分批處理）
4. ✅ 自動執行垂直文字生成（分批處理）
5. ✅ 顯示完整摘要和統計（總時間、成功/失敗數量）

#### 自訂參數

```bash
./run_batch.sh \
  --lines lines.txt \
  --fonts_dir fonts \
  --bgs_dir backgrounds \
  --out_dir_h out_h \
  --out_dir_v out_v \
  --n_per_line 20 \
  --box_jitter 2,2 \
  --last_resort_font NotoSansTC-Regular.ttf \
  --seed 20 \
  --num_workers 6 \
  --batch_size 10000
```

#### 查看幫助

```bash
./run_batch.sh --help
```

---

### 方法 2: Python 批次腳本（單獨執行水平或垂直）

如果你只想執行其中一個方向，或需要更精細的控制：

#### 僅水平文字生成（60萬行）

```bash
python3 run_batch.py \
  --lines lines.txt \
  --fonts_dir fonts \
  --bgs_dir backgrounds \
  --out_dir out_h \
  --n_per_line 20 \
  --box_jitter 2,2 \
  --last_resort_font NotoSansTC-Regular.ttf \
  --seed 20 \
  --num_workers 6 \
  --batch_size 10000
```

#### 僅垂直文字生成（60萬行）

```bash
python3 run_batch.py \
  --lines lines.txt \
  --fonts_dir fonts \
  --bgs_dir backgrounds \
  --out_dir out_v \
  --n_per_line 20 \
  --vertical \
  --box_jitter 2,2 \
  --last_resort_font NotoSansTC-Regular.ttf \
  --seed 20 \
  --num_workers 6 \
  --batch_size 10000
```

---

### 方法 3: 手動執行特定範圍

如果你只想處理特定範圍的行數（適合除錯或補跑失敗的批次）：

```bash
# 處理第 0-10000 行（水平）
python3 synth.py \
  --lines lines.txt \
  --fonts_dir fonts \
  --bgs_dir backgrounds \
  --out_dir out_h \
  --n_per_line 20 \
  --box_jitter 2,2 \
  --no_debug_boxes \
  --last_resort_font NotoSansTC-Regular.ttf \
  --seed 20 \
  --num_workers 12 \
  --start_line 0 \
  --end_line 10000

# 處理第 10000-20000 行（垂直）
python3 synth.py \
  --lines lines.txt \
  --fonts_dir fonts \
  --bgs_dir backgrounds \
  --out_dir out_v \
  --n_per_line 20 \
  --vertical \
  --box_jitter 2,2 \
  --no_debug_boxes \
  --last_resort_font NotoSansTC-Regular.ttf \
  --seed 20 \
  --num_workers 12 \
  --start_line 10000 \
  --end_line 20000
```

---

## 參數說明

### run_batch.sh 專用參數

- `--out_dir_h`: 水平文字輸出資料夾（預設：out_h）
- `--out_dir_v`: 垂直文字輸出資料夾（預設：out_v）

### 批次處理共用參數

- `--lines`: 輸入文字檔案（預設：lines.txt）
- `--fonts_dir`: 字體資料夾（預設：fonts）
- `--bgs_dir`: 背景圖片資料夾（預設：backgrounds）
- `--n_per_line`: 每行生成幾張圖片（預設：20）
- `--box_jitter`: 字框隨機偏移量（預設：2,2）
- `--last_resort_font`: 最後備援字體（預設：NotoSansTC-Regular.ttf）
- `--seed`: 隨機種子（預設：20）
- `--num_workers`: 每批次使用的 CPU worker 數（預設：6）
- `--batch_size`: 每個批次處理的行數（預設：10000）
  - 60萬行資料，batch_size=10000 會分成 60 個批次
  - 可以根據記憶體情況調整此值

### synth.py 專用參數

- `--start_line`: 起始行號（從 0 開始）
- `--end_line`: 結束行號（不含），None 表示到結尾
- `--vertical`: 是否垂直排版

---

## 注意事項

### 1. 檔案命名
使用 `start_line` 和 `end_line` 時，檔案名稱會基於全域行號，因此不同批次生成的檔案不會衝突。

例如：
- 批次 1 (lines 0-9999): 生成 `000000_h_0.jpg` 到 `009999_h_19.jpg`
- 批次 2 (lines 10000-19999): 生成 `010000_h_0.jpg` 到 `019999_h_19.jpg`

### 2. manifest.jsonl
每個批次會追加到同一個 manifest.jsonl，無需手動合併。

### 3. 錯誤記錄
- 每個方向（水平/垂直）有獨立的 `error_log.txt`
- 建議處理完成後檢查：
  ```bash
  cat out_h/error_log.txt
  cat out_v/error_log.txt
  ```

### 4. 記憶體管理
- 預設 `batch_size=10000` 適合大多數情況
- 記憶體不足時降低：`--batch_size 5000`
- 記憶體充足時提高：`--batch_size 20000`

### 5. 批次失敗處理
- Python 腳本會追蹤失敗的批次
- 可以手動重新執行失敗的範圍（參考方法 3）

---

## 範例工作流程

### 🚀 推薦工作流程：60萬行一次跑完

```bash
# 一個指令搞定全部！
./run_batch.sh

# 腳本會顯示：
# - 總行數：600,000
# - 每個方向圖片數：12,000,000 (600,000 × 20)
# - 總圖片數：24,000,000
# - 預估大小：~1.8TB
#
# 然後詢問是否繼續 (y/n)
```

### 替代工作流程：分開執行

```bash
# 1. 先生成水平文字（60萬行，每行20張 = 1200萬張）
python3 run_batch.py \
  --lines lines.txt \
  --out_dir out_h \
  --n_per_line 20 \
  --batch_size 10000

# 2. 再生成垂直文字（60萬行，每行20張 = 1200萬張）
python3 run_batch.py \
  --lines lines.txt \
  --out_dir out_v \
  --n_per_line 20 \
  --vertical \
  --batch_size 10000

# 3. 檢查輸出
ls -lh out_h/ | head
ls -lh out_v/ | head

# 4. 檢查錯誤（如果有）
cat out_h/error_log.txt
cat out_v/error_log.txt
```

---

## 效能建議

- **CPU**: `--num_workers 6` 適合 6 核心 CPU
  - 建議設為 CPU 核心數或略少
  - 可以用 `nproc` 查看核心數

- **記憶體**: 每個批次約需 2-4GB
  - 根據字體數量和背景圖大小調整
  - 建議保留系統至少 4GB 記憶體

- **磁碟空間**: 每張圖約 50-100KB
  - 60萬行 × 20張 × 2方向 = 2400萬張
  - 約需 1.2TB - 2.4TB 空間

- **處理時間**: 視 CPU 和磁碟速度而定
  - 每批次（1萬行）約 5-30 分鐘
  - 60個批次 × 2方向 = 總共約 10-60 小時
  - 建議使用 `screen` 或 `tmux` 在背景執行

---

## 疑難排解

### ❓ 某個批次失敗

```bash
# 查看哪個批次失敗
# Python 腳本會顯示失敗的批次號

# 重新執行特定範圍（例如批次 5: lines 50000-59999）
python3 synth.py \
  --start_line 50000 \
  --end_line 60000 \
  --lines lines.txt \
  --out_dir out_h \
  --n_per_line 20 \
  --box_jitter 2,2 \
  --no_debug_boxes \
  --last_resort_font NotoSansTC-Regular.ttf \
  --seed 20 \
  --num_workers 12
```

### ❓ 記憶體不足

```bash
# 方法 1: 降低 batch_size
./run_batch.sh --batch_size 5000

# 方法 2: 降低 num_workers
./run_batch.sh --num_workers 6 --batch_size 5000
```

### ❓ 需要暫停並繼續

```bash
# 1. 按 Ctrl+C 中斷

# 2. 查看目前進度（最後一個生成的檔案）
ls -lt out_h/*.jpg | head -1
# 假設看到 049999_h_19.jpg，表示處理到第 49999 行

# 3. 從下一個批次開始（50000）
python3 run_batch.py \
  --start_line 50000 \
  --lines lines.txt \
  --out_dir out_h \
  --n_per_line 20 \
  --batch_size 10000
```

### ❓ 如何在背景執行

```bash
# 使用 nohup（簡單但較難監控）
nohup ./run_batch.sh > batch.log 2>&1 &
tail -f batch.log

# 使用 screen（推薦）
screen -S ocr_synth
./run_batch.sh
# 按 Ctrl+A 然後 D 離開
# 重新連接：screen -r ocr_synth

# 使用 tmux（推薦）
tmux new -s ocr_synth
./run_batch.sh
# 按 Ctrl+B 然後 D 離開
# 重新連接：tmux attach -t ocr_synth
```

### ❓ 檢查進度

```bash
# 查看已生成的檔案數量
echo "Horizontal: $(find out_h -name '*.jpg' | wc -l) images"
echo "Vertical: $(find out_v -name '*.jpg' | wc -l) images"

# 查看最新生成的檔案
ls -lht out_h/*.jpg | head -5
ls -lht out_v/*.jpg | head -5

# 查看磁碟使用量
du -sh out_h out_v
```

---

## 快速參考

```bash
# 最簡單：一鍵全跑
./run_batch.sh

# 只跑水平
python3 run_batch.py --out_dir out_h

# 只跑垂直
python3 run_batch.py --out_dir out_v --vertical

# 補跑特定範圍
python3 synth.py --start_line 50000 --end_line 60000 [其他參數...]

# 查看幫助
./run_batch.sh --help
python3 run_batch.py --help
python3 synth.py --help
```
