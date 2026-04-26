import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC_DIR = os.path.join(BASE_DIR, "doc")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

def parse_txt_to_dict(filename):
    filepath = os.path.join(DOC_DIR, filename)
    if not os.path.exists(filepath):
        return {}
    
    result = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_parsing = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("Mã"):
            start_parsing = True
            continue
            
        if start_parsing:
            parts = line.split('\t')
            if len(parts) >= 2:
                ma = parts[0].strip()
                ten = parts[1].strip()
                extra = [p.strip() for p in parts[2:] if p.strip()] if len(parts) > 2 else []
                result[ma] = {
                    "ten": ten,
                    "extra": extra
                }
    return result

def main():
    os.makedirs(CONFIG_DIR, exist_ok=True)

    danh_muc_files = {
        "danh_muc_dan_toc.json": "Danh mục dân tộc.txt",
        "danh_muc_gioi_tinh.json": "Danh mục giới tính.txt",
        "danh_muc_quoc_gia.json": "Danh mục quốc gia.txt",
        "danh_muc_tinh_thanh_cu.json": "Danh mục tỉnh thành cũ.txt",
        "danh_muc_tinh_thanh_hien_nay.json": "Danh mục tỉnh thành hiện nay.txt"
    }

    for json_name, txt_name in danh_muc_files.items():
        data = parse_txt_to_dict(txt_name)
        out_path = os.path.join(CONFIG_DIR, json_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Created {out_path}")

    templates = {
        "chung_chi_so": {
            "id": "chung_chi_so",
            "name": "Chung Chi So",
            "description": "Template trích xuất dữ liệu Chứng Chỉ Số",
            "fields": []
        },
        "van_bang_dai_hoc": {
            "id": "van_bang_dai_hoc",
            "name": "Van Bang Dai Hoc",
            "description": "Template trích xuất dữ liệu Văn Bằng Đại Học",
            "fields": []
        }
    }
    
    templates_path = os.path.join(CONFIG_DIR, "templates.json")
    with open(templates_path, 'w', encoding='utf-8') as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)
    print(f"Created {templates_path}")

if __name__ == "__main__":
    main()
