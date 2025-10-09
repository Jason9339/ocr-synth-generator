#!/bin/bash
# 檢查輸出路徑設定

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    檢查輸出路徑設定                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 檢查預設路徑
H_PATH="/ocr_out_h"
V_PATH="/ocr_out_v"

echo "預設輸出路徑："
echo "  水平: $H_PATH"
echo "  垂直: $V_PATH"
echo ""

# 檢查路徑是否存在
echo "路徑狀態："
if [ -d "$H_PATH" ]; then
    h_size=$(du -sh "$H_PATH" 2>/dev/null | cut -f1)
    h_files=$(find "$H_PATH" -name "*.jpg" 2>/dev/null | wc -l)
    echo "  ✓ $H_PATH 存在 (大小: $h_size, 圖片: $h_files)"
else
    echo "  - $H_PATH 不存在（尚未生成）"
fi

if [ -d "$V_PATH" ]; then
    v_size=$(du -sh "$V_PATH" 2>/dev/null | cut -f1)
    v_files=$(find "$V_PATH" -name "*.jpg" 2>/dev/null | wc -l)
    echo "  ✓ $V_PATH 存在 (大小: $v_size, 圖片: $v_files)"
else
    echo "  - $V_PATH 不存在（尚未生成）"
fi

echo ""

# 檢查檔案系統類型
echo "檔案系統類型："
for path in "$H_PATH" "$V_PATH"; do
    parent_path=$(dirname "$path")
    if [ -d "$parent_path" ]; then
        fs_type=$(stat -f -c %T "$parent_path" 2>/dev/null || echo "unknown")

        if echo "$fs_type" | grep -qiE 'nfs|cifs|smb'; then
            echo "  ⚠ $path 父目錄 ($parent_path) 在網路檔案系統 ($fs_type)"
            echo "     建議改為本機路徑"
        else
            echo "  ✓ $path 父目錄 ($parent_path) 在本機檔案系統 ($fs_type)"
        fi
    else
        echo "  - $path 父目錄不存在"
    fi
done

echo ""

# 檢查可用空間
echo "可用空間："
parent_path=$(dirname "$H_PATH")
if [ -d "$parent_path" ]; then
    avail_gb=$(df -BG --output=avail "$parent_path" 2>/dev/null | tail -1 | tr -d ' G' || echo "0")
    echo "  $parent_path: ${avail_gb}GB 可用"

    if [ "$avail_gb" -lt 200 ] 2>/dev/null; then
        echo "  ⚠ 警告：可用空間少於建議的 200GB"
    else
        echo "  ✓ 可用空間充足"
    fi
else
    echo "  無法檢查（目錄不存在）"
fi

echo ""
echo "完成檢查"
