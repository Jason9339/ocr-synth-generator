import argparse
import warnings
from pathlib import Path
from PIL import Image, ImageOps

def scan_and_fix_images(directory: Path, fix: bool = False):
    """
    掃描指定目錄下的所有圖片，檢查是否有格式問題，並可選擇自動修正。
    """
    image_paths = [p for p in directory.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp")]
    
    if not image_paths:
        print(f"在 '{directory}' 中找不到任何圖片檔案。")
        return

    print(f"開始掃描 {len(image_paths)} 張圖片... (模式: {'自動修正' if fix else '僅偵測'})")

    issues_found = 0
    fixed_count = 0

    for i, path in enumerate(image_paths):
        print(f"  處理中 ({i+1}/{len(image_paths)}): {path.name}", end='\r')
        
        has_issue = False
        issue_messages = []

        try:
            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")
                
                with Image.open(path) as img:
                    # 執行最可能觸發警告的操作
                    ImageOps.exif_transpose(img) 
                    
                    if "P" in img.mode or (img.mode == 'RGBA' and 'transparency' in img.info):
                         if any("Palette" in str(w.message) for w in caught_warnings):
                            has_issue = True

                if caught_warnings:
                    for w in caught_warnings:
                        msg = str(w.message)
                        if "Palette" in msg or "EXIF" in msg:
                            has_issue = True
                            issue_messages.append(msg)
            
            if has_issue:
                issues_found += 1
                print(" " * 80, end='\r') 
                print(f"[發現問題] 檔案: {path.name}")
                for msg in set(issue_messages):
                    print(f"  - 原因: {msg}")

                if fix:
                    try:
                        print("  -> 執行修正...")
                        with Image.open(path) as img_to_fix:
                            # 轉換為標準 RGB 模式
                            fixed_img = img_to_fix.convert("RGB")
                            
                            # <<<< 主要修改點在這裡 <<<<
                            # 直接儲存 RGB 版本的圖片，不傳遞舊的、可能已損壞的 EXIF 資料。
                            # 這會移除所有 EXIF 資訊，但能確保檔案是乾淨的。
                            fixed_img.save(path, quality=95)
                        
                        fixed_count += 1
                        print("  -> 修正完成！")
                    except Exception as e:
                        print(f"  -> 修正失敗: {e}")

        except Exception as e:
            print(" " * 80, end='\r')
            print(f"[錯誤] 無法開啟或處理檔案: {path.name}, 原因: {e}")

    print("\n掃描完成！")
    # 這裡的 issues_found 仍會是修正前的數量，這是正常的
    if fix:
        print(f"總共發現並嘗試修正 {issues_found} 個有問題的檔案。")
        print(f"成功修正了 {fixed_count} 個檔案。")
    else:
        print(f"總共發現 {issues_found} 個有問題的檔案。")

def main():
    parser = argparse.ArgumentParser(description="掃描圖片目錄，找出有格式問題的圖片並可選擇自動修正。")
    parser.add_argument("dir", type=str, help="要掃描的圖片目錄路徑 (例如: backgrounds)")
    parser.add_argument("--fix", action="store_true", help="啟用自動修正模式，會覆寫有問題的圖片。")
    args = parser.parse_args()

    scan_and_fix_images(Path(args.dir), args.fix)

if __name__ == "__main__":
    main()