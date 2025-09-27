import argparse
from pathlib import Path
from PIL import ImageFont

def check_all_fonts(fonts_dir: Path):
    """
    遍歷指定資料夾中的所有字體檔案，檢查它們是否可以被 Pillow 正常加載和使用。
    """
    if not fonts_dir.is_dir():
        print(f"錯誤：找不到資料夾 '{fonts_dir}'")
        return

    print(f"--- 開始檢查 '{fonts_dir}' 資料夾中的所有字體 ---")
    
    font_files = [p for p in fonts_dir.glob("*") if p.suffix.lower() in (".ttf", ".otf")]
    
    if not font_files:
        print("在資料夾中沒有找到任何 .ttf 或 .otf 字體檔案。")
        return

    good_fonts = []
    bad_fonts = []
    sample_char = '字'  # 用一個常用字來測試
    font_size = 32     # 任意指定一個大小即可

    for font_path in font_files:
        print(f"正在檢查: {font_path.name} ... ", end="")
        try:
            # 1. 嘗試加載字體
            font = ImageFont.truetype(str(font_path), size=font_size)
            
            # 2. 嘗試使用字體進行基本操作 (這是觸發錯誤的關鍵步驟)
            font.getbbox(sample_char)
            
            # 如果上面兩步都沒問題，就認為是好字體
            print("✅ OK")
            good_fonts.append(font_path.name)
            
        except OSError as e:
            # 捕捉到特定的 OSError
            print(f"❌ 失敗 (OSError)")
            bad_fonts.append((font_path.name, str(e)))
        except Exception as e:
            # 捕捉其他可能的錯誤，例如檔案格式不正確
            print(f"❌ 失敗 (其他錯誤)")
            bad_fonts.append((font_path.name, str(e)))

    # --- 輸出總結報告 ---
    print("\n--- 字體檢查完畢 ---")

    if not bad_fonts:
        print("\n🎉 恭喜！所有字體都通過了檢查。")
        if good_fonts:
            print("可用字體列表：")
            for name in sorted(good_fonts):
                print(f"  - {name}")
    else:
        print("\n⚠️ 發現以下有問題的字體，請將它們從 fonts 資料夾中移除或更換：")
        for name, error_msg in bad_fonts:
            print(f"  - 檔名: {name}")
            print(f"    錯誤訊息: {error_msg}")
        
        if good_fonts:
            print("\n✅ 以下字體是正常的：")
            for name in sorted(good_fonts):
                print(f"  - {name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="一個用來檢查字體檔案是否損毀或有問題的工具。")
    parser.add_argument(
        "--fonts_dir", 
        type=str, 
        default="fonts", 
        help="包含 .ttf/.otf 字體檔案的資料夾路徑。"
    )
    args = parser.parse_args()
    
    check_all_fonts(Path(args.fonts_dir))