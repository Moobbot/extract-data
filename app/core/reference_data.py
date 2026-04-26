import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC_DIR = os.path.join(BASE_DIR, "doc")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

# Khởi tạo thư mục config nếu chưa có
os.makedirs(CONFIG_DIR, exist_ok=True)


def parse_txt_to_dict(filename):
    filepath = os.path.join(DOC_DIR, filename)
    if not os.path.exists(filepath):
        return {}

    result = {}
    with open(filepath, "r", encoding="utf-8") as f:
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
            parts = line.split("\t")
            if len(parts) >= 2:
                ma = parts[0].strip()
                ten = parts[1].strip()
                extra = (
                    [p.strip() for p in parts[2:] if p.strip()]
                    if len(parts) > 2
                    else []
                )
                result[ma] = {"ten": ten, "extra": extra}
    return result


def load_or_create_json(json_name, txt_source=None, default_data=None):
    json_path = os.path.join(CONFIG_DIR, json_name)

    # Nếu chưa có file JSON, thì lấy từ nguồn TXT hoặc data mặc định rồi ghi ra JSON
    if not os.path.exists(json_path):
        if txt_source:
            data = parse_txt_to_dict(txt_source)
        else:
            data = default_data or {}

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    # Nếu đã có JSON, ưu tiên đọc từ JSON để người dùng dễ dàng chỉnh sửa sau này
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


# Load dữ liệu danh mục từ config/ (Nếu chưa có sẽ tự parse từ doc/)
DANH_MUC_DAN_TOC = load_or_create_json("danh_muc_dan_toc.json", "Danh mục dân tộc.txt")
DANH_MUC_GIOI_TINH = load_or_create_json(
    "danh_muc_gioi_tinh.json", "Danh mục giới tính.txt"
)
DANH_MUC_QUOC_GIA = load_or_create_json(
    "danh_muc_quoc_gia.json", "Danh mục quốc gia.txt"
)
DANH_MUC_TINH_THANH_CU = load_or_create_json(
    "danh_muc_tinh_thanh_cu.json", "Danh mục tỉnh thành cũ.txt"
)
DANH_MUC_TINH_THANH_HIEN_NAY = load_or_create_json(
    "danh_muc_tinh_thanh_hien_nay.json", "Danh mục tỉnh thành hiện nay.txt"
)

# Load thêm các danh mục mới
DANH_MUC_HINH_THUC_DAO_TAO = load_or_create_json(
    "danh_muc_hinh_thuc_dao_tao.json", "Danh mục hình thức đào tạo.txt"
)
DANH_MUC_LOAI_TOT_NGHIEP = load_or_create_json(
    "danh_muc_loai_tot_nghiep.json", "Danh mục loại tốt nghiệp.txt"
)
DANH_MUC_NGOAI_NGU = load_or_create_json(
    "danh_muc_ngoai_ngu.json", "Danh mục ngoại ngữ.txt"
)
DANH_MUC_TRINH_DO_DAO_TAO = load_or_create_json(
    "danh_muc_trinh_do_dao_tao.json", "Danh mục trình độ đào tạo.txt"
)
DANH_MUC_TRANG_THAI_SO_HOA = load_or_create_json(
    "danh_muc_trang_thai_so_hoa.json", "Danh mục trạng thái số hóa.txt"
)
DANH_MUC_BAC_KHUNG_TRINH_DO = load_or_create_json(
    "danh_muc_bac_khung_trinh_do.json", "Danh mục bậc khung trình độ.txt"
)
DANH_MUC_NGANH = load_or_create_json("danh_muc_nganh.json", "Danh mục ngành.txt")

# Khởi tạo Templates chuẩn
default_templates = {
    "chung_chi_so": {
        "id": "chung_chi_so",
        "name": "Chung Chi So",
        "description": "Template trích xuất dữ liệu Chứng Chỉ Số",
        "fields": [],
    },
    "van_bang_dai_hoc": {
        "id": "van_bang_dai_hoc",
        "name": "Van Bang Dai Hoc",
        "description": "Template trích xuất dữ liệu Văn Bằng Đại Học",
        "fields": [],
    },
}
TEMPLATES = load_or_create_json("templates.json", default_data=default_templates)


def get_reference_data():
    """Trả về toàn bộ danh mục và cấu trúc template cho API (nếu cần)"""
    return {
        "danh_muc": {
            "dan_toc": DANH_MUC_DAN_TOC,
            "gioi_tinh": DANH_MUC_GIOI_TINH,
            "quoc_gia": DANH_MUC_QUOC_GIA,
            "tinh_thanh_cu": DANH_MUC_TINH_THANH_CU,
            "tinh_thanh_hien_nay": DANH_MUC_TINH_THANH_HIEN_NAY,
            "hinh_thuc_dao_tao": DANH_MUC_HINH_THUC_DAO_TAO,
            "loai_tot_nghiep": DANH_MUC_LOAI_TOT_NGHIEP,
            "ngoai_ngu": DANH_MUC_NGOAI_NGU,
            "trinh_do_dao_tao": DANH_MUC_TRINH_DO_DAO_TAO,
            "trang_thai_so_hoa": DANH_MUC_TRANG_THAI_SO_HOA,
            "bac_khung_trinh_do": DANH_MUC_BAC_KHUNG_TRINH_DO,
            "nganh": DANH_MUC_NGANH,
        },
        "templates": TEMPLATES,
    }
