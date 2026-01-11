# Quick Start Guide

這個快速指南將帶您在 5 分鐘內生成第一批合成 OCR 資料。

## 前置需求

- Python 3.8+
- 已安裝依賴套件
- 有字型檔案和背景圖片

## 1. 安裝 (30 秒)

```bash
git clone https://github.com/YOUR_USERNAME/ocr-synth-generator.git
cd ocr-synth-generator
pip install -r requirements.txt
```

## 2. 準備資料 (1 分鐘)

確認您有:
- ✅ `fonts/` 目錄中有字型檔案
- ✅ `backgrounds/` 目錄中有背景圖片

測試範例已包含在 `examples/sample_lines.txt`

## 3. 生成圖片 (2 分鐘)

### 使用範例資料快速測試

```bash
python3 src/synth.py \
    --lines examples/sample_lines.txt \
    --fonts_dir fonts \
    --bgs_dir backgrounds \
    --out_dir output/quickstart \
    --manifest output/quickstart/manifest.jsonl \
    --n_per_line 2 \
    --num_workers 2
```

這將生成 20 張圖片 (10 行 × 2 張/行)。

### 查看結果

```bash
# 查看生成的圖片
ls -lh output/quickstart/*.jpg | head -5

# 查看 manifest
head -3 output/quickstart/manifest.jsonl
```

## 4. 生成垂直文字 (額外 2 分鐘)

```bash
python3 src/synth.py \
    --lines examples/sample_lines.txt \
    --fonts_dir fonts \
    --bgs_dir backgrounds \
    --out_dir output/quickstart_v \
    --manifest output/quickstart_v/manifest.jsonl \
    --n_per_line 2 \
    --vertical \
    --num_workers 2
```

## 5. 使用自己的文本

創建您自己的文本檔案:

```bash
cat > data/my_text.txt << EOF
您的第一行文字
您的第二行文字
您的第三行文字
EOF
```

生成圖片:

```bash
python3 src/synth.py \
    --lines data/my_text.txt \
    --fonts_dir fonts \
    --bgs_dir backgrounds \
    --out_dir output/my_output \
    --manifest output/my_output/manifest.jsonl \
    --n_per_line 10 \
    --num_workers 4
```

## 常見問題

### Q: 缺少字型

**A:** 確保 `fonts/` 目錄中至少有一個 .ttf 或 .otf 檔案。推薦使用 Noto Sans TC。

### Q: 沒有背景圖片

**A:** 在 `backgrounds/` 目錄中放入一些 .jpg 或 .png 圖片作為背景紋理。

### Q: 生成速度慢

**A:** 增加 `--num_workers` 參數值 (建議設為 CPU 核心數)。

### Q: 記憶體不足

**A:** 減少 `--num_workers` 或處理較小批次。

## 下一步

### 大規模生成

查看 [docs/STEP_BY_STEP_5K.md](docs/STEP_BY_STEP_5K.md) 了解如何處理大型資料集。

### 更多範例

查看 [docs/EXAMPLES.md](docs/EXAMPLES.md) 了解進階用法和客製化選項。

### LMDB 轉換

將資料轉換為訓練用 LMDB 格式:

```bash
python3 src/convert_to_lmdb.py \
    --src output/quickstart \
    --dst quickstart.lmdb \
    --verify
```

## 驗證安裝

測試所有核心功能:

```bash
# 檢查字型
python3 scripts/check_fonts.py

# 生成測試資料
python3 src/synth.py --lines examples/sample_lines.txt \
    --out_dir output/test --manifest output/test/manifest.jsonl \
    --n_per_line 2

# 驗證圖片
python3 scripts/check_images.py output/test/

# 清理
rm -rf output/test
```

如果以上都成功,恭喜!您已經準備好開始生成 OCR 訓練資料了。

---

**需要幫助?** 查看完整文檔或在 GitHub 上開 issue。
