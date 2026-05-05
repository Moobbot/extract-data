from app.services.ai_providers import AIProviderFactory
from app.services.prompt_manager import PromptManager
import os
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

import pandas as pd


def process_image_task(
    image_path: str,
    agent: str,
    output_format: str,
    save_to_file: bool = False,
    agent_config: Optional[Dict[str, Any]] = None,
    template_id: str = "default",
    source_filename: Optional[str] = None,
    source_folder: Optional[str] = None,
    task_id: str = "unknown",
):
    """
    Background task to process an image.
    """
    resolved_source_filename = source_filename
    resolved_source_folder = source_folder
    if task_id != "unknown" and (
        not resolved_source_filename or not resolved_source_folder
    ):
        try:
            from app.core.db import get_task_by_id

            task_row = get_task_by_id(task_id)
            if task_row:
                if not resolved_source_filename:
                    resolved_source_filename = task_row.get("filename")
                if not resolved_source_folder:
                    resolved_source_folder = task_row.get("folder_path")
        except Exception:
            pass

    def _clean_json_string(raw_text: str) -> str:
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _save_excel_from_json(data: Any, excel_path: str) -> Optional[str]:

        try:
            sheets = {}

            def _frame_from_rows(
                rows: Any, headers: Optional[Any] = None
            ) -> Optional[pd.DataFrame]:
                if not isinstance(rows, list) or not rows:
                    return None
                if not isinstance(rows[0], dict):
                    return None
                frame = pd.DataFrame(rows)
                if isinstance(headers, list) and headers:
                    ordered_headers = [h for h in headers if h in frame.columns]
                    remaining = [c for c in frame.columns if c not in ordered_headers]
                    frame = frame[ordered_headers + remaining]
                return frame

            # Prefer OCR-style table extraction first (tables[].rows + optional headers)
            table_frames = []
            queue = [data]
            while queue:
                current = queue.pop(0)
                if isinstance(current, dict):
                    rows_frame = _frame_from_rows(
                        current.get("rows"), current.get("headers")
                    )
                    if rows_frame is not None:
                        table_frames.append(rows_frame)

                    tables = current.get("tables")
                    if isinstance(tables, list):
                        for table in tables:
                            if isinstance(table, dict):
                                frame = _frame_from_rows(
                                    table.get("rows"), table.get("headers")
                                )
                                if frame is not None:
                                    table_frames.append(frame)

                    for key, value in current.items():
                        if key == "tables":
                            continue
                        if isinstance(value, (dict, list)):
                            queue.append(value)
                elif isinstance(current, list):
                    for item in current:
                        if isinstance(item, (dict, list)):
                            queue.append(item)

            if table_frames:
                for idx, frame in enumerate(table_frames, start=1):
                    sheet_name = "Sheet1" if idx == 1 else f"Table{idx}"
                    sheets[sheet_name] = frame

            if not sheets and isinstance(data, list):
                if (
                    data
                    and isinstance(data[0], list)
                    and data[0]
                    and isinstance(data[0][0], dict)
                ):
                    flat_rows = []
                    for chunk in data:
                        if isinstance(chunk, list):
                            flat_rows.extend([r for r in chunk if isinstance(r, dict)])
                    sheets["Sheet1"] = pd.DataFrame(flat_rows)
                else:
                    sheets["Sheet1"] = pd.DataFrame(data)
            elif not sheets and isinstance(data, dict):
                found_list = False
                for key, value in data.items():
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        sheet_name = str(key)[:31]
                        sheets[sheet_name] = pd.DataFrame(value)
                        found_list = True

                if not found_list:
                    sheets["Sheet1"] = pd.DataFrame([data])
            elif not sheets:
                sheets["Sheet1"] = pd.DataFrame([{"result": data}])

            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                for sheet_name, frame in sheets.items():
                    frame.to_excel(writer, sheet_name=sheet_name, index=False)

            return excel_path
        except Exception:
            return None

    def _extract_records_for_mapping(payload: Any) -> Any:
        """
        Normalize common OCR JSON shapes into row records for template mapping.
        Examples handled:
        - {"tables": [{"rows": [...]}, ...]}
        - {"result": [...]}
        - [{"tables": ...}, ...]
        """
        if isinstance(payload, str):
            text = _clean_json_string(payload)
            try:
                decoded = json.loads(text)
                return _extract_records_for_mapping(decoded)
            except Exception:
                return payload

        if isinstance(payload, dict):
            for nested_key in ("data", "content", "text", "raw_text", "rendered_text"):
                nested = payload.get(nested_key)
                if isinstance(nested, (dict, list)):
                    extracted = _extract_records_for_mapping(nested)
                    if extracted is not nested:
                        return extracted
                elif isinstance(nested, str):
                    extracted = _extract_records_for_mapping(nested)
                    if extracted is not nested:
                        return extracted

            if isinstance(payload.get("result"), list):
                return payload["result"]

            tables = payload.get("tables")
            if isinstance(tables, list):
                rows = []
                for table in tables:
                    if isinstance(table, dict) and isinstance(table.get("rows"), list):
                        rows.extend([r for r in table["rows"] if isinstance(r, dict)])
                if rows:
                    return rows

            if isinstance(payload.get("rows"), list):
                return payload["rows"]

            return payload

        if isinstance(payload, list):
            rows = []
            has_table_like = False
            for item in payload:
                if isinstance(item, dict) and (
                    isinstance(item.get("tables"), list)
                    or isinstance(item.get("result"), list)
                    or isinstance(item.get("rows"), list)
                ):
                    has_table_like = True
                extracted = _extract_records_for_mapping(item)
                if isinstance(extracted, list):
                    rows.extend([r for r in extracted if isinstance(r, dict)])
                elif isinstance(extracted, dict):
                    rows.append(extracted)

            if has_table_like:
                return rows
            return payload

        return payload

    def _collect_image_paths(folder_path: str) -> list[str]:
        valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        collected = []
        base_path = Path(folder_path)
        if not base_path.exists() or not base_path.is_dir():
            return collected

        for file_path in base_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                collected.append(str(file_path))
        return sorted(collected)

    def _save_combined_excel(rows: list[dict], excel_path: str) -> Optional[str]:
        try:
            if not rows:
                return None
            frame = pd.DataFrame(rows)
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                frame.to_excel(writer, sheet_name="Sheet1", index=False)
            return excel_path
        except Exception:
            return None

    def _numeric_stt(value: Any) -> Optional[int]:
        text = str(value or "").strip()
        return int(text) if text.isdigit() else None

    def _sort_rows_by_stt(rows: list[dict]) -> list[dict]:
        indexed_rows = [(idx, row) for idx, row in enumerate(rows)]
        numeric_count = sum(
            1
            for _, row in indexed_rows
            if _numeric_stt(row.get("STT")) is not None
        )
        if numeric_count < 2:
            return rows
        return [
            row
            for _, row in sorted(
                indexed_rows,
                key=lambda item: (
                    _numeric_stt(item[1].get("STT")) is None,
                    _numeric_stt(item[1].get("STT")) or 0,
                    item[0],
                ),
            )
        ]

    try:
        # 1. Get Provider
        try:
            ai_provider = AIProviderFactory.get_provider(agent, agent_config)
        except ValueError as e:
            from app.core.db import update_task_status

            update_task_status(task_id, "failed", error=str(e))
            return {"error": str(e), "status": "failed"}

        # 2. Get Prompt (Truyền cấu trúc template vào nếu có)
        from app.core.reference_data import get_reference_data

        ref_data = get_reference_data()
        templates = ref_data.get("templates", {})

        prompt = PromptManager.get_prompt(output_format)

        if template_id != "default" and template_id in templates:
            # Gắn thêm cấu trúc mẫu vào prompt để AI xuất ra đúng field
            fields = templates[template_id].get("fields", [])
            fields_str = ", ".join([f["name"] for f in fields])
            prompt += f"\n\nIMPORTANT: You must extract EXACTLY the following fields in your JSON output: {fields_str}"

        is_folder_input = os.path.isdir(image_path)
        if is_folder_input:
            folder_files = _collect_image_paths(image_path)
            if not folder_files:
                from app.core.db import update_task_status

                err_msg = "No valid images found in folder"
                update_task_status(task_id, "failed", error=err_msg)
                return {"error": err_msg, "status": "failed"}

            folder_results = []
            failed_files = []
            combined_lv1_rows: list[dict] = []
            combined_template_rows: list[dict] = []
            combined_content: list[str] = []
            api_base_url = None
            api_json_path = None
            api_excel_path = None

            for index, current_image_path in enumerate(folder_files, start=1):
                if not os.path.isfile(current_image_path):
                    continue

                try:
                    content_result = ai_provider.generate_content(
                        current_image_path, prompt
                    )
                except Exception as e:
                    err_msg = f"AI generation failed for {os.path.basename(current_image_path)}: {str(e)}"
                    failed_files.append(
                        {
                            "filename": os.path.basename(current_image_path),
                            "error": err_msg,
                        }
                    )
                    continue

                if isinstance(content_result, dict):
                    content = content_result.get("text", "")
                    api_base_url = content_result.get("base_url", api_base_url)
                    api_json_path = content_result.get("api_json_path")
                    api_excel_path = content_result.get("api_excel_path")
                else:
                    content = content_result

                combined_content.append(
                    f"### {os.path.basename(current_image_path)}\n\n{content}"
                )

                parsed = None
                if output_format == "json":
                    try:
                        parsed = json.loads(_clean_json_string(content))
                    except json.JSONDecodeError:
                        parsed = None

                parsed_lv1 = None
                if parsed is not None:
                    parsed_lv1 = json.loads(json.dumps(parsed, ensure_ascii=False))

                def _flatten_mapped_rows(value: Any) -> Any:
                    if not isinstance(value, list):
                        return value
                    flattened = []
                    for item in value:
                        if isinstance(item, list):
                            flattened.extend(
                                [row for row in item if isinstance(row, dict)]
                            )
                        else:
                            flattened.append(item)
                    return flattened

                if parsed is not None and template_id != "default":
                    from app.core.mapper import map_extracted_data

                    parsed = _extract_records_for_mapping(parsed)

                    if isinstance(parsed, list):
                        parsed = map_extracted_data(parsed, template_id)
                        parsed = _flatten_mapped_rows(parsed)
                    elif isinstance(parsed, dict):
                        if "result" in parsed and isinstance(parsed["result"], list):
                            parsed["result"] = map_extracted_data(
                                parsed["result"], template_id
                            )
                            parsed["result"] = _flatten_mapped_rows(parsed["result"])
                        else:
                            parsed = map_extracted_data(parsed, template_id)

                if parsed_lv1 is not None:
                    raw_rows = _extract_records_for_mapping(parsed_lv1)
                    if isinstance(raw_rows, list):
                        combined_lv1_rows.extend(
                            [row for row in raw_rows if isinstance(row, dict)]
                        )
                    elif isinstance(raw_rows, dict):
                        combined_lv1_rows.append(raw_rows)

                if parsed is not None:
                    mapped_rows = _extract_records_for_mapping(parsed)
                    if isinstance(mapped_rows, list):
                        combined_template_rows.extend(
                            [row for row in mapped_rows if isinstance(row, dict)]
                        )
                    elif isinstance(mapped_rows, dict):
                        combined_template_rows.append(mapped_rows)

                folder_results.append(
                    {
                        "filename": os.path.basename(current_image_path),
                        "ocr_text": content,
                        "tables": (
                            parsed.get("tables", []) if isinstance(parsed, dict) else []
                        ),
                        "text_lines": (
                            parsed.get("text_lines", [])
                            if isinstance(parsed, dict)
                            else []
                        ),
                        "kv_pairs": (
                            parsed.get("kv_pairs", {})
                            if isinstance(parsed, dict)
                            else {}
                        ),
                        "table_count": (
                            parsed.get("table_count", 0)
                            if isinstance(parsed, dict)
                            else 0
                        ),
                    }
                )

            if not folder_results:
                from app.core.db import update_task_status

                first_error = (
                    failed_files[0]["error"]
                    if failed_files
                    else "Folder processing failed"
                )
                update_task_status(task_id, "failed", error=first_error)
                return {
                    "error": first_error,
                    "status": "failed",
                    "failed_files": failed_files,
                    "total_files": len(folder_files),
                    "success_count": 0,
                    "failed_count": len(failed_files),
                }

            saved_path = None
            saved_excel = None
            saved_excel_lv1 = None
            saved_excel_template = None

            if save_to_file:
                from app.core.config import settings

                def _safe_name(value: str) -> str:
                    cleaned = "".join(
                        ch if ch not in '<>:"/\\|?*' else "_" for ch in value
                    )
                    return cleaned.strip().strip(".") or "output"

                display_filename = resolved_source_filename or os.path.basename(
                    image_path
                )
                base_name = _safe_name(
                    os.path.splitext(os.path.basename(display_filename))[0]
                )
                folder_label = ""
                if resolved_source_folder:
                    folder_label = _safe_name(
                        os.path.basename(os.path.normpath(resolved_source_folder))
                    )
                base_slug = f"{folder_label}_{base_name}" if folder_label else base_name
                ext = "md" if output_format == "markdown" else "json"
                output_filename = f"{base_slug}.{ext}"
                now = datetime.now()
                dated_output_dir = os.path.join(
                    settings.OUTPUT_DIR,
                    now.strftime("%Y"),
                    now.strftime("%m"),
                    now.strftime("%d"),
                )
                os.makedirs(dated_output_dir, exist_ok=True)
                saved_path = os.path.join(dated_output_dir, output_filename)
                excel_name_prefix = f"excel_{base_slug}"
                excel_lv1_path = os.path.join(
                    dated_output_dir, f"{excel_name_prefix}_lv1.xlsx"
                )
                excel_template_path = os.path.join(
                    dated_output_dir, f"{excel_name_prefix}_template.xlsx"
                )

                if output_format == "json":
                    if template_id == "van_bang_dai_hoc":
                        combined_lv1_rows = _sort_rows_by_stt(combined_lv1_rows)
                        combined_template_rows = _sort_rows_by_stt(
                            combined_template_rows
                        )

                    with open(saved_path, "w", encoding="utf-8") as f:
                        json.dump(folder_results, f, ensure_ascii=False, indent=2)

                    saved_excel_lv1 = _save_combined_excel(
                        combined_lv1_rows, excel_lv1_path
                    )

                    # Ghi vào template Excel nếu template_id có cấu hình file template
                    if template_id != "default" and combined_template_rows:
                        from app.services.excel_writer import (
                            write_rows_to_template,
                            get_template_excel_path,
                            get_template_sheet_name,
                        )
                        tmpl_file = get_template_excel_path(template_id)
                        tmpl_sheet = get_template_sheet_name(template_id)
                        if tmpl_file:
                            saved_excel_template = write_rows_to_template(
                                rows=combined_template_rows,
                                template_path=tmpl_file,
                                output_path=excel_template_path,
                                sheet_name=tmpl_sheet,
                            )
                        else:
                            saved_excel_template = _save_combined_excel(
                                combined_template_rows, excel_template_path
                            )
                    elif combined_template_rows:
                        saved_excel_template = _save_combined_excel(
                            combined_template_rows, excel_template_path
                        )

                    saved_excel = saved_excel_template or saved_excel_lv1
                else:
                    with open(saved_path, "w", encoding="utf-8") as f:
                        f.write("\n\n".join(combined_content))

            from app.core.db import update_task_status

            update_task_status(
                task_id, "success", json_path=saved_path, excel_path=saved_excel
            )

            result_status = "partial_success" if failed_files else "success"

            return {
                "status": result_status,
                "agent": agent,
                "provider": agent,
                "format": output_format,
                "filename": resolved_source_filename or os.path.basename(image_path),
                "folder_name": (
                    os.path.basename(os.path.normpath(resolved_source_folder))
                    if resolved_source_folder
                    else None
                ),
                "content": "\n\n".join(combined_content),
                "saved_to": saved_path,
                "saved_excel": saved_excel,
                "saved_excel_lv1": saved_excel_lv1,
                "saved_excel_template": saved_excel_template,
                "api_base_url": api_base_url,
                "api_json_path": api_json_path,
                "api_excel_path": api_excel_path,
                "total_files": len(folder_files),
                "success_count": len(folder_results),
                "failed_count": len(failed_files),
                "failed_files": failed_files,
            }

        # 3. Generate
        try:
            content_result = ai_provider.generate_content(image_path, prompt)
        except Exception as e:
            err_msg = f"AI generation failed: {str(e)}"
            from app.core.db import update_task_status

            update_task_status(task_id, "failed", error=err_msg)
            return {"error": err_msg, "status": "failed"}

        api_base_url = None
        api_json_path = None
        api_excel_path = None

        if isinstance(content_result, dict):
            content = content_result.get("text", "")
            api_base_url = content_result.get("base_url", "http://localhost:8000")
            api_json_path = content_result.get("api_json_path")
            api_excel_path = content_result.get("api_excel_path")
        else:
            content = content_result

        # 4. Save to file if requested
        saved_path = None
        saved_excel = None
        saved_excel_lv1 = None
        saved_excel_template = None
        if save_to_file:
            from app.core.config import settings
            import requests

            def _safe_name(value: str) -> str:
                cleaned = "".join(ch if ch not in '<>:"/\\|?*' else "_" for ch in value)
                return cleaned.strip().strip(".") or "output"

            display_filename = resolved_source_filename or os.path.basename(image_path)
            base_name = _safe_name(
                os.path.splitext(os.path.basename(display_filename))[0]
            )
            folder_label = ""
            if resolved_source_folder:
                folder_label = _safe_name(
                    os.path.basename(os.path.normpath(resolved_source_folder))
                )
            base_slug = f"{folder_label}_{base_name}" if folder_label else base_name
            ext = "md" if output_format == "markdown" else "json"
            output_filename = f"{base_slug}.{ext}"
            now = datetime.now()
            dated_output_dir = os.path.join(
                settings.OUTPUT_DIR,
                now.strftime("%Y"),
                now.strftime("%m"),
                now.strftime("%d"),
            )
            os.makedirs(dated_output_dir, exist_ok=True)
            saved_path = os.path.join(dated_output_dir, output_filename)
            excel_name_prefix = f"excel_{base_slug}"
            excel_lv1_path = os.path.join(
                dated_output_dir, f"{excel_name_prefix}_lv1.xlsx"
            )
            excel_template_path = os.path.join(
                dated_output_dir, f"{excel_name_prefix}_template.xlsx"
            )

            # Nếu API có file JSON chuẩn và định dạng yêu cầu là json, thử tải về thay vì ghi text chay
            downloaded_json = False
            if output_format == "json" and api_json_path and api_base_url:
                try:
                    res = requests.post(
                        f"{api_base_url}/download",
                        json={"path": api_json_path},
                        timeout=60,
                    )
                    res.raise_for_status()
                    with open(saved_path, "wb") as f:
                        f.write(res.content)
                    downloaded_json = True
                except Exception:
                    pass

            # Nếu không tải được hoặc định dạng là markdown, lưu content như cũ
            if not downloaded_json:
                with open(saved_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # Xử lý JSON mapping & Excel
            if output_format == "json":
                # Đọc nội dung JSON để parse
                parsed = None
                parsed_lv1 = None
                if downloaded_json:
                    try:
                        with open(saved_path, "r", encoding="utf-8") as f:
                            parsed = json.load(f)
                    except Exception:
                        pass
                else:
                    try:
                        parsed = json.loads(_clean_json_string(content))
                    except json.JSONDecodeError:
                        pass

                if parsed is not None:
                    parsed_lv1 = json.loads(json.dumps(parsed, ensure_ascii=False))

                def _flatten_mapped_rows(value: Any) -> Any:
                    if not isinstance(value, list):
                        return value
                    flattened = []
                    for item in value:
                        if isinstance(item, list):
                            flattened.extend(
                                [row for row in item if isinstance(row, dict)]
                            )
                        else:
                            flattened.append(item)
                    return flattened

                # ÁP DỤNG MAPPING Ở ĐÂY
                if parsed is not None and template_id != "default":
                    from app.core.mapper import map_extracted_data

                    parsed = _extract_records_for_mapping(parsed)

                    if isinstance(parsed, list):
                        parsed = map_extracted_data(parsed, template_id)
                        parsed = _flatten_mapped_rows(parsed)
                    elif isinstance(parsed, dict):
                        # Đôi khi LightOnOCR trả về dict chứa key "result" -> list
                        if "result" in parsed and isinstance(parsed["result"], list):
                            parsed["result"] = map_extracted_data(
                                parsed["result"], template_id
                            )
                            parsed["result"] = _flatten_mapped_rows(parsed["result"])
                        else:
                            parsed = map_extracted_data(parsed, template_id)

                    # Lưu lại JSON sau khi map, đè lên file cũ
                    with open(saved_path, "w", encoding="utf-8") as f:
                        json.dump(parsed, f, ensure_ascii=False, indent=2)

                # Build LV1 excel from raw parsed JSON (before template mapping).
                if parsed_lv1 is not None:
                    saved_excel_lv1 = _save_excel_from_json(parsed_lv1, excel_lv1_path)

                # Build template excel from mapped/final JSON.
                if parsed is not None:
                    rows_for_excel = _extract_records_for_mapping(parsed)
                    if not isinstance(rows_for_excel, list):
                        rows_for_excel = [rows_for_excel] if isinstance(rows_for_excel, dict) else []
                    rows_for_excel = [r for r in rows_for_excel if isinstance(r, dict)]

                    if template_id != "default" and rows_for_excel:
                        from app.services.excel_writer import (
                            write_rows_to_template,
                            get_template_excel_path,
                            get_template_sheet_name,
                        )
                        tmpl_file = get_template_excel_path(template_id)
                        tmpl_sheet = get_template_sheet_name(template_id)
                        if tmpl_file:
                            saved_excel_template = write_rows_to_template(
                                rows=rows_for_excel,
                                template_path=tmpl_file,
                                output_path=excel_template_path,
                                sheet_name=tmpl_sheet,
                            )
                        else:
                            saved_excel_template = _save_excel_from_json(
                                parsed, excel_template_path
                            )
                    else:
                        saved_excel_template = _save_excel_from_json(
                            parsed, excel_template_path
                        )
                    saved_excel = saved_excel_template

                # Fallback: if JSON parsing fails entirely, try downloading API Excel.
                if (
                    not saved_excel
                    and template_id == "default"
                    and api_excel_path
                    and api_base_url
                ):
                    excel_out = os.path.join(dated_output_dir, f"{base_name}.xlsx")
                    try:
                        res = requests.post(
                            f"{api_base_url}/download",
                            json={"path": api_excel_path},
                            timeout=60,
                        )
                        res.raise_for_status()
                        with open(excel_out, "wb") as f:
                            f.write(res.content)
                        saved_excel = excel_out
                        saved_excel_lv1 = excel_out
                        saved_excel_template = excel_out
                    except Exception:
                        pass

        from app.core.db import update_task_status

        update_task_status(
            task_id, "success", json_path=saved_path, excel_path=saved_excel
        )

        return {
            "status": "success",
            "agent": agent,
            "provider": agent,
            "format": output_format,
            "filename": resolved_source_filename or os.path.basename(image_path),
            "folder_name": (
                os.path.basename(os.path.normpath(resolved_source_folder))
                if resolved_source_folder
                else None
            ),
            "content": content,
            "saved_to": saved_path,
            "saved_excel": saved_excel,
            "saved_excel_lv1": saved_excel_lv1,
            "saved_excel_template": saved_excel_template,
            "api_base_url": api_base_url,
            "api_json_path": api_json_path,
            "api_excel_path": api_excel_path,
        }

    except Exception as e:
        from app.core.db import update_task_status

        update_task_status(task_id, "failed", error=str(e))
        # Let Celery record the real exception payload (exc_type, traceback, ...).
        raise
    finally:
        # Cleanup uploaded file if needed?
        # For now, let's keep it or manage cleanup policy separately
        # os.remove(image_path)
        pass
