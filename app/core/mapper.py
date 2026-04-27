import os
import json
import unicodedata
from typing import Any
from app.core.reference_data import get_reference_data


COMMON_ERROR_MAP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config",
    "field_mapping_common_errors.json",
)


def load_common_error_mapping() -> dict:
    if not os.path.exists(COMMON_ERROR_MAP_PATH):
        return {}
    try:
        with open(COMMON_ERROR_MAP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def unaccent_and_lower(text: str) -> str:
    """Loại bỏ dấu tiếng Việt và chuyển thành chữ thường để so sánh."""
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("đ", "d")


def find_category_code(value: str, category_dict: dict) -> str:
    """
    Tìm tên chuẩn của giá trị trong danh mục dựa vào so sánh không dấu, không phân biệt hoa thường.
    Trả về tên chuẩn (không phải mã) nếu tìm thấy, ngược lại trả về chuỗi rỗng.
    """
    if not value or not isinstance(value, str):
        return ""

    search_val = unaccent_and_lower(value.strip())

    for code, info in category_dict.items():
        # Kiểm tra tên chính
        if unaccent_and_lower(info.get("ten", "")) == search_val:
            return info.get("ten")
        # Kiểm tra các tên phụ (extra)
        for extra_name in info.get("extra", []):
            if unaccent_and_lower(extra_name) == search_val:
                return info.get("ten")

    return ""


def map_extracted_data(data, template_id: str):
    """
    Map dữ liệu trích xuất được từ OCR với danh mục chuẩn dựa trên template_id.
    """
    ref_data = get_reference_data()
    templates = ref_data.get("templates", {})
    categories = ref_data.get("danh_muc", {})
    common_error_map = load_common_error_mapping().get(template_id, {})
    alias_map = common_error_map.get("aliases", {})

    if template_id not in templates:
        return data

    template_fields = templates[template_id].get("fields", [])

    def _normalize_key(text: str) -> str:
        return unaccent_and_lower(text or "")

    def _canonical_gender(value: Any) -> str:
        normalized = _normalize_key(str(value).strip())
        if normalized == "nam":
            return "Nam"
        if normalized == "nu":
            return "Nữ"
        if normalized == "khac":
            return "Khác"
        return ""

    def _looks_like_date(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        parts = text.split("/")
        if len(parts) != 3:
            return False
        if not all(part.isdigit() for part in parts):
            return False
        day, month, year = parts
        return 1 <= len(day) <= 2 and 1 <= len(month) <= 2 and len(year) == 4

    def _looks_like_flexible_date(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        parts = text.split("/")
        if len(parts) not in (2, 3):
            return False
        if not all(part.isdigit() for part in parts):
            return False
        if len(parts) == 2:
            day, month = parts
            return 1 <= len(day) <= 2 and 1 <= len(month) <= 2
        day, month, year = parts
        return 1 <= len(day) <= 2 and 1 <= len(month) <= 2 and len(year) in (2, 4)

    def _normalize_flexible_date(value: Any) -> str:
        text = str(value or "").strip()
        if not _looks_like_flexible_date(text):
            return text
        parts = text.split("/")
        if len(parts) == 3 and len(parts[2]) == 2:
            parts[2] = f"20{parts[2]}"
        return "/".join(parts)

    def _looks_like_rank(value: Any) -> bool:
        text = _normalize_key(str(value or "").strip())
        return text in {
            "xuat sac",
            "gioi",
            "kha",
            "trung binh kha",
            "trung binh",
            "yeu",
            "kem",
        }

    def _looks_like_degree_number(value: Any) -> bool:
        text = str(value or "").strip().replace(" ", "")
        return bool(text) and text.isdigit() and len(text) >= 4

    def _extract_with_aliases(record: dict, field_name: str) -> Any:
        wanted = _normalize_key(field_name)
        aliases = [wanted]
        aliases.extend(_normalize_key(a) for a in alias_map.get(field_name, []))

        for k, v in record.items():
            if _normalize_key(str(k)) in aliases:
                return v
        return ""

    def _fix_van_bang_shift(mapped: dict) -> dict:
        if template_id != "van_bang_dai_hoc":
            return mapped

        name_key = "Họ, chữ đệm và tên"
        gender_key = "Giới tính"
        dob_key = "Ngày, tháng, năm sinh"
        rank_key = "Xếp loại/hạng tốt nghiệp"
        degree_key = "Số hiệu bằng"
        issue_date_key = "Ngày tháng năm cấp bằng"
        signer_key = "Họ, chữ đệm, tên người ký bằng"
        note_key = "Ghi chú"

        gender = _canonical_gender(mapped.get(gender_key, ""))
        next_gender = _canonical_gender(mapped.get(dob_key, ""))
        rank_is_date = _looks_like_date(mapped.get(rank_key, ""))

        # When gender column accidentally receives the tail of person's name,
        # and the true gender shifts into the next column, shift values right.
        if not gender and next_gender and rank_is_date:
            extra_name = str(mapped.get(gender_key, "")).strip()
            base_name = str(mapped.get(name_key, "")).strip()
            if extra_name:
                mapped[name_key] = (base_name + " " + extra_name).strip()

            old_dob = mapped.get(dob_key, "")
            old_rank = mapped.get(rank_key, "")
            old_degree = mapped.get(degree_key, "")
            old_signer = mapped.get(signer_key, "")
            old_note = mapped.get(note_key, "")

            mapped[gender_key] = old_dob
            mapped[dob_key] = old_rank
            mapped[rank_key] = old_degree
            mapped[degree_key] = old_signer
            mapped[signer_key] = old_note
            mapped[note_key] = ""

        # Nếu số hiệu bằng và ngày cấp bằng bị tráo vị trí sau khi shift,
        # đổi lại: số hiệu bằng phải là chuỗi số, ngày cấp bằng phải giống ngày.
        degree_value = str(mapped.get(degree_key, "")).strip()
        issue_date_value = str(mapped.get(issue_date_key, "")).strip()
        if _looks_like_flexible_date(degree_value) and _looks_like_degree_number(
            issue_date_value
        ):
            mapped[degree_key], mapped[issue_date_key] = (
                issue_date_value,
                _normalize_flexible_date(degree_value),
            )

        # Nếu ngày sinh bị lặp bằng giới tính, bỏ giá trị lỗi để tránh làm bẩn dữ liệu.
        dob_value = str(mapped.get(dob_key, "")).strip()
        if _canonical_gender(dob_value) and _canonical_gender(
            dob_value
        ) == _canonical_gender(mapped.get(gender_key, "")):
            mapped[dob_key] = ""

        # Nếu xếp loại trôi sang cột người ký thì kéo về đúng cột.
        rank_value = str(mapped.get(rank_key, "")).strip()
        signer_value = str(mapped.get(signer_key, "")).strip()
        if not rank_value and _looks_like_rank(signer_value):
            mapped[rank_key] = signer_value
            mapped[signer_key] = ""

        if common_error_map.get("carry_date_from_signer_to_issue_date"):
            signer_value = str(mapped.get(signer_key, "")).strip()
            note_value = str(mapped.get(note_key, "")).strip()

            if not str(mapped.get(issue_date_key, "")).strip() and _looks_like_date(
                signer_value
            ):
                mapped[issue_date_key] = signer_value
                mapped[signer_key] = ""

            if not str(mapped.get(issue_date_key, "")).strip() and _looks_like_date(
                note_value
            ):
                mapped[issue_date_key] = note_value
                mapped[note_key] = ""

        # Chuẩn hoá định dạng ngày cấp bằng (hỗ trợ dd/mm/yy).
        if str(mapped.get(issue_date_key, "")).strip():
            mapped[issue_date_key] = _normalize_flexible_date(
                mapped.get(issue_date_key, "")
            )

        # Fallback nhẹ: nếu số bằng bị OCR dạt sang cột người ký,
        # đổi chỗ để bảo toàn số bằng (không đụng các cột khác).
        degree_value = str(mapped.get(degree_key, "")).strip()
        signer_value = str(mapped.get(signer_key, "")).strip()
        if not _looks_like_degree_number(degree_value) and _looks_like_degree_number(
            signer_value
        ):
            mapped[degree_key], mapped[signer_key] = signer_value, degree_value

        # Sau swap có thể phát sinh xếp loại nằm ở cột người ký.
        rank_value = str(mapped.get(rank_key, "")).strip()
        signer_value = str(mapped.get(signer_key, "")).strip()
        if not rank_value and _looks_like_rank(signer_value):
            mapped[rank_key] = signer_value
            mapped[signer_key] = ""

        return mapped

    def _extract_rows_from_ocr_payload(obj: Any) -> list:
        rows = []
        if not isinstance(obj, dict):
            return rows

        tables = obj.get("tables")
        if isinstance(tables, list):
            for table in tables:
                if not isinstance(table, dict):
                    continue
                table_rows = table.get("rows")
                if isinstance(table_rows, list):
                    rows.extend([r for r in table_rows if isinstance(r, dict)])

        result_rows = obj.get("result")
        if isinstance(result_rows, list):
            rows.extend([r for r in result_rows if isinstance(r, dict)])

        return rows

    def _map_one_record(record: dict) -> dict:
        mapped = {}
        for field in template_fields:
            field_name = field.get("name", "")
            if not field_name:
                continue

            category_name = field.get("category")
            raw_value = _extract_with_aliases(record, field_name)

            if raw_value is None:
                raw_value = ""

            mapped[field_name] = raw_value

        mapped = _fix_van_bang_shift(mapped)

        for field in template_fields:
            field_name = field.get("name", "")
            if not field_name:
                continue
            category_name = field.get("category")
            raw_value = mapped.get(field_name, "")

            if category_name and category_name in categories:
                if isinstance(raw_value, list):
                    mapped[field_name] = [
                        find_category_code(str(item), categories[category_name])
                        for item in raw_value
                    ]
                else:
                    mapped[field_name] = find_category_code(
                        str(raw_value), categories[category_name]
                    )
            else:
                mapped[field_name] = raw_value

        return mapped

    if isinstance(data, list):
        extracted_rows = []
        for item in data:
            extracted_rows.extend(_extract_rows_from_ocr_payload(item))

        if extracted_rows:
            return [_map_one_record(row) for row in extracted_rows]

        return [
            _map_one_record(item) if isinstance(item, dict) else item for item in data
        ]

    if isinstance(data, dict):
        extracted_rows = _extract_rows_from_ocr_payload(data)
        if extracted_rows:
            return [_map_one_record(row) for row in extracted_rows]
        return _map_one_record(data)

    return data
