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

    def _compact_key(text: str) -> str:
        normalized = _normalize_key(text)
        return "".join(ch for ch in normalized if ch.isalnum())

    def _canonical_gender(value: Any) -> str:
        normalized = _normalize_key(str(value).strip())
        if normalized == "nam":
            return "Nam"
        # OCR thường đọc "Nữ" thành "Ng", "Ngữ" hoặc "Ngu".
        if normalized in {"nu", "ng", "ngu"}:
            return "Nữ"
        if normalized == "khac":
            return "Khác"
        return ""

    def _looks_like_date(value: Any) -> bool:
        parsed = _parse_flexible_date(value)
        return parsed is not None and bool(parsed[2])

    def _looks_like_flexible_date(value: Any) -> bool:
        return _parse_flexible_date(value) is not None

    def _repair_month(num: int) -> int:
        if 1 <= num <= 12:
            return num
        # OCR hay thêm nhầm tiền tố '1' cho tháng (vd: 16 thay vì 06).
        if 10 <= num <= 19 and 1 <= (num % 10) <= 9:
            return num % 10
        return num

    def _parse_flexible_date(value: Any) -> tuple[int, int, str] | None:
        text = str(value or "").strip().replace("-", "/")
        if not text:
            return None
        parts = text.split("/")
        if len(parts) not in (2, 3):
            return None
        if not all(part.isdigit() for part in parts):
            return None

        day = int(parts[0])
        month = _repair_month(int(parts[1]))

        if not (1 <= day <= 31 and 1 <= month <= 12):
            return None

        year = ""
        if len(parts) == 3:
            year_raw = parts[2]
            if len(year_raw) == 2:
                year = f"20{year_raw}"
            elif len(year_raw) == 3 and year_raw.startswith("1"):
                # OCR hay mất chữ số đầu của năm: 2013 -> 113.
                year = f"20{year_raw[-2:]}"
            elif len(year_raw) == 4:
                year = year_raw
            else:
                return None

        return day, month, year

    def _normalize_flexible_date(value: Any) -> str:
        parsed = _parse_flexible_date(value)
        if parsed is None:
            return str(value or "").strip()
        day, month, year = parsed
        if year:
            return f"{day:02d}/{month:02d}/{year}"
        return f"{day:02d}/{month:02d}"

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

    def _looks_like_book_number(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        compact = text.replace(" ", "").upper()
        return "/" in text or "-LKTQ" in compact or (
            "K" in compact and any(ch.isdigit() for ch in compact)
        )

    def _has_person_title(value: Any) -> bool:
        normalized = _normalize_key(str(value or "").strip())
        for title in ("ong", "ba"):
            if normalized.startswith(title):
                tail = normalized[len(title) :]
                return not tail or tail[0].isspace() or not ("a" <= tail[0] <= "z")
        return False

    def _field_aliases(field_name: str) -> list[str]:
        aliases = [_normalize_key(field_name)]
        aliases.extend(_normalize_key(a) for a in alias_map.get(field_name, []))
        return aliases

    def _candidate_values(record: dict, field_name: str) -> list[tuple[str, Any]]:
        aliases = set(_field_aliases(field_name))
        return [
            (str(k), v)
            for k, v in record.items()
            if _normalize_key(str(k)) in aliases
        ]

    def _raw_values_by_compact_aliases(
        record: dict, aliases: set[str]
    ) -> list[tuple[str, Any]]:
        return [
            (str(k), v)
            for k, v in record.items()
            if _compact_key(str(k)) in aliases
        ]

    def _extract_with_aliases(record: dict, field_name: str) -> Any:
        candidates = _candidate_values(record, field_name)
        return candidates[0][1] if candidates else ""

    def _extract_template_value(record: dict, field_name: str) -> Any:
        if template_id != "van_bang_dai_hoc":
            return _extract_with_aliases(record, field_name)

        degree_key = "Số hiệu bằng"
        book_key = "Số vào sổ gốc cấp văn bằng"

        if field_name == degree_key:
            candidates = _candidate_values(record, field_name)
            for _, value in candidates:
                if _looks_like_degree_number(value):
                    return value
            return candidates[0][1] if candidates else ""

        if field_name == book_key:
            candidates = _candidate_values(record, field_name)
            for _, value in candidates:
                if _looks_like_book_number(value):
                    return value

            # Một vài trang OCR nhầm header cột "Số vào sổ" thành
            # "Số hiệu bằng"; chỉ dùng làm số vào sổ nếu value có dạng sổ.
            for _, value in _raw_values_by_compact_aliases(record, {"sohieubang"}):
                if _looks_like_book_number(value):
                    return value

            return candidates[0][1] if candidates else ""

        return _extract_with_aliases(record, field_name)

    def _fix_van_bang_shift(mapped: dict, record: dict | None = None) -> dict:
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

        # Một số bảng OCR nhầm header, đưa tên người vào cột "Tên văn bằng"
        # với tiền tố Ông/Bà. Chỉ sửa khi field họ tên đang rỗng để tránh
        # ghi đè tên văn bằng thật.
        degree_name_value = str(mapped.get("Tên văn bằng", "")).strip()
        if (
            not str(mapped.get(name_key, "")).strip()
            and _has_person_title(degree_name_value)
        ):
            mapped[name_key] = degree_name_value
            mapped["Tên văn bằng"] = ""

        gender = _canonical_gender(mapped.get(gender_key, ""))
        next_gender = _canonical_gender(mapped.get(dob_key, ""))
        rank_is_date = _looks_like_date(mapped.get(rank_key, ""))

        # When gender column accidentally receives the tail of person's name,
        # and the true gender shifts into the next column, shift values right.
        shifted_columns = next_gender and rank_is_date and (
            not gender
            or _looks_like_rank(mapped.get(degree_key, ""))
            or _looks_like_degree_number(mapped.get(issue_date_key, ""))
            or _looks_like_flexible_date(mapped.get(signer_key, ""))
        )
        if shifted_columns:
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
            mapped[signer_key] = (
                old_note
                if (
                    _looks_like_flexible_date(old_note)
                    or _looks_like_degree_number(old_note)
                    or _looks_like_rank(old_note)
                )
                else ""
            )
            mapped[note_key] = ""

        # Một biến thể nhẹ hơn: cột giới tính chứa phần cuối của họ tên,
        # nhưng các cột sau đó không bị shift. Khi đó chỉ ghép tên và để
        # giới tính trống, không đoán giới tính nếu OCR không cung cấp.
        elif (
            not gender
            and not next_gender
            and str(mapped.get(gender_key, "")).strip()
            and _looks_like_date(mapped.get(dob_key, ""))
            and _looks_like_rank(mapped.get(rank_key, ""))
        ):
            extra_name = str(mapped.get(gender_key, "")).strip()
            base_name = str(mapped.get(name_key, "")).strip()
            mapped[name_key] = (base_name + " " + extra_name).strip()
            mapped[gender_key] = ""

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

            if not str(
                mapped.get(issue_date_key, "")
            ).strip() and _looks_like_flexible_date(signer_value):
                mapped[issue_date_key] = signer_value
                mapped[signer_key] = ""

            if not str(
                mapped.get(issue_date_key, "")
            ).strip() and _looks_like_flexible_date(note_value):
                mapped[issue_date_key] = note_value
                mapped[note_key] = ""

        # Chuẩn hoá định dạng ngày sinh nếu nhận được ngày hợp lệ.
        if str(mapped.get(dob_key, "")).strip():
            mapped[dob_key] = _normalize_flexible_date(mapped.get(dob_key, ""))

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

        canonical_gender = _canonical_gender(mapped.get(gender_key, ""))
        if canonical_gender:
            mapped[gender_key] = canonical_gender

        # Cột OCR "Ký, ghi tên" là chữ ký/người nhận trong danh sách,
        # không phải "Họ, chữ đệm, tên người ký bằng" của template import.
        if record:
            signature_values = [
                str(value).strip()
                for _, value in _raw_values_by_compact_aliases(
                    record, {"kyghiten", "kyhenten"}
                )
                if str(value or "").strip()
            ]
            signer_value = str(mapped.get(signer_key, "")).strip()
            if signer_value and signer_value in signature_values:
                mapped[signer_key] = ""

        return mapped

    def _postprocess_mapped_rows(rows: list[dict]) -> list[dict]:
        if template_id != "van_bang_dai_hoc":
            return rows

        issue_date_key = "Ngày tháng năm cấp bằng"
        year_counts: dict[str, int] = {}

        for row in rows:
            parsed = _parse_flexible_date(row.get(issue_date_key, ""))
            if parsed and parsed[2]:
                year_counts[parsed[2]] = year_counts.get(parsed[2], 0) + 1

        if not year_counts:
            return rows

        common_year = max(year_counts.items(), key=lambda item: item[1])[0]
        for row in rows:
            parsed = _parse_flexible_date(row.get(issue_date_key, ""))
            if parsed and not parsed[2]:
                day, month, _ = parsed
                row[issue_date_key] = f"{day:02d}/{month:02d}/{common_year}"

        return rows

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
            raw_value = _extract_template_value(record, field_name)

            if raw_value is None:
                raw_value = ""

            mapped[field_name] = raw_value

        mapped = _fix_van_bang_shift(mapped, record)

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
            return _postprocess_mapped_rows(
                [_map_one_record(row) for row in extracted_rows]
            )

        mapped_rows = [
            _map_one_record(item) if isinstance(item, dict) else item for item in data
        ]
        if all(isinstance(row, dict) for row in mapped_rows):
            return _postprocess_mapped_rows(mapped_rows)
        return mapped_rows

    if isinstance(data, dict):
        extracted_rows = _extract_rows_from_ocr_payload(data)
        if extracted_rows:
            return _postprocess_mapped_rows(
                [_map_one_record(row) for row in extracted_rows]
            )
        return _map_one_record(data)

    return data
