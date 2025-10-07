# OCR 合成器 - 批次處理模式

## 🎯 快速開始

### 一鍵執行全部（最簡單）

```bash
./run_batch.sh
```

這個指令會：
- ✅ 自動處理水平文字生成
- ✅ 自動處理垂直文字生成
- ✅ 顯示進度和摘要
- ✅ 處理 60 萬行沒問題！

## 📚 完整文檔

詳細使用說明請參考：[BATCH_USAGE.md](BATCH_USAGE.md)

## 🔧 三種使用方式

### 1️⃣ 一鍵全跑（推薦）
```bash
./run_batch.sh
```

### 2️⃣ 只跑水平或垂直
```bash
# 只跑水平
python3 run_batch.py --out_dir out_h

# 只跑垂直
python3 run_batch.py --out_dir out_v --vertical
```

### 3️⃣ 手動指定範圍
```bash
python3 synth.py --start_line 0 --end_line 10000 [其他參數...]
```

## 📊 關鍵參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--batch_size` | 10000 | 每批次處理的行數 |
| `--num_workers` | 6 | 每批次的 CPU 核心數 |
| `--n_per_line` | 20 | 每行生成幾張圖 |
| `--seed` | 20 | 隨機種子（可重現結果）|

## 💾 預估資源需求

以 60 萬行為例：
- **圖片數量**: 2400 萬張（水平 + 垂直）
- **磁碟空間**: 約 1.2-2.4 TB
- **處理時間**: 約 10-60 小時（視 CPU 而定）
- **記憶體**: 每批次約 2-4GB

## 🆘 常見問題

### Q: 記憶體不足怎麼辦？
```bash
./run_batch.sh --batch_size 5000 --num_workers 6
```

### Q: 如何在背景執行？
```bash
# 使用 screen（推薦）
screen -S ocr_synth
./run_batch.sh
# 按 Ctrl+A 然後 D 離開

# 重新連接
screen -r ocr_synth
```

### Q: 如何查看進度？
```bash
# 查看已生成的圖片數
echo "Horizontal: $(find out_h -name '*.jpg' | wc -l)"
echo "Vertical: $(find out_v -name '*.jpg' | wc -l)"

# 查看磁碟使用量
du -sh out_h out_v
```

### Q: 某個批次失敗怎麼辦？
```bash
# 重新執行該範圍（例如 50000-60000）
python3 synth.py --start_line 50000 --end_line 60000 [其他參數...]
```

## 📁 輸出檔案

```
out_h/                    # 水平文字輸出
├── 000000_h_0.jpg
├── 000000_h_1.jpg
├── ...
├── manifest.jsonl        # 圖片和標籤對應
└── error_log.txt         # 錯誤記錄

out_v/                    # 垂直文字輸出
├── 000000_v_0.jpg
├── 000000_v_1.jpg
├── ...
├── manifest.jsonl
└── error_log.txt
```

## 🔍 更多資訊

- 完整使用說明：[BATCH_USAGE.md](BATCH_USAGE.md)
- 查看幫助：`./run_batch.sh --help`
- 原始腳本：[synth.py](synth.py)
