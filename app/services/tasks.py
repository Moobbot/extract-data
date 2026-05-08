from app.services.ai_providers import AIProviderFactory
from app.services.prompt_manager import PromptManager
import os
import json
import shutil
import tempfile
import zipfile
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
    folder_content_spool_path: Optional[str] = None

    def _int_env(name: str, default: int) -> int:
        try:
            return max(0, int(os.getenv(name, str(default))))
        except ValueError:
            return default

    content_preview_limit = _int_env("TASK_RESULT_CONTENT_PREVIEW_CHARS", 12000)
    per_file_ocr_preview_limit = _int_env("TASK_RESULT_OCR_TEXT_PREVIEW_CHARS", 2000)

    def _truncate_text(text: Any, limit: int) -> tuple[str, bool]:
        value = "" if text is None else str(text)
        if limit and len(value) > limit:
            return value[:limit], True
        return value, False

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

    def _save_json_artifact(data: Any, json_path: str) -> Optional[str]:
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return json_path
        except Exception:
            return None

    try:
        # 1. Get Provider
        try:
            ai_provider = AIProviderFactory.get_provider(agent, agent_config)
        except ValueError as e:
            from app.core.db import update_task_status

            update_task_status(task_id, "failed", error=str(e))
            return {"error": str(e), "status": "failed"}

        # 2. Get Prompt. Keep OCR prompt template-agnostic; field mapping happens
        # after the raw/LV1 response is parsed.
        prompt = PromptManager.get_prompt(output_format)

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
            content_preview_parts: list[str] = []
            content_preview_chars = 0
            content_preview_truncated = False
            api_base_url = None
            api_json_path = None
            api_excel_path = None
            saved_raw_lightonocr_json = None
            saved_lv1_json = None
            folder_save_context: Optional[dict[str, str]] = None
            per_image_dir = None
            per_image_artifacts: list[dict[str, Any]] = []
            raw_lightonocr_entries: list[dict[str, Any]] = []
            combined_lv1_payloads: list[dict[str, Any]] = []
            saved_per_image_zip = None

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
                if task_id != "unknown":
                    base_slug = "_".join(
                        [
                            base_slug,
                            _safe_name(template_id or "default"),
                            _safe_name(task_id.split("-")[0]),
                        ]
                    )
                elif template_id and template_id != "default":
                    base_slug = f"{base_slug}_{_safe_name(template_id)}"
                ext = "md" if output_format == "markdown" else "json"
                now = datetime.now()
                dated_output_dir = os.path.join(
                    settings.OUTPUT_DIR,
                    now.strftime("%Y"),
                    now.strftime("%m"),
                    now.strftime("%d"),
                )
                os.makedirs(dated_output_dir, exist_ok=True)
                zip_dir = os.path.join(settings.OUTPUT_DIR, "per_image_zips")
                os.makedirs(zip_dir, exist_ok=True)
                folder_save_context = {
                    "base_slug": base_slug,
                    "dated_output_dir": dated_output_dir,
                    "saved_path": os.path.join(dated_output_dir, f"{base_slug}.{ext}"),
                    "raw_lightonocr_path": os.path.join(
                        dated_output_dir, f"{base_slug}_raw_lightonocr.json"
                    ),
                    "lv1_json_path": os.path.join(
                        dated_output_dir, f"{base_slug}_lv1.json"
                    ),
                    "excel_lv1_path": os.path.join(
                        dated_output_dir, f"excel_{base_slug}_lv1.xlsx"
                    ),
                    "excel_template_path": os.path.join(
                        dated_output_dir, f"excel_{base_slug}_template.xlsx"
                    ),
                    "per_image_zip_path": os.path.join(
                        zip_dir, f"{task_id}_per_image_artifacts.zip"
                    ),
                }
                if output_format == "json":
                    per_image_dir = os.path.join(
                        dated_output_dir, f"{base_slug}_per_image"
                    )
                    os.makedirs(per_image_dir, exist_ok=True)

            if save_to_file and output_format != "json":
                fd, folder_content_spool_path = tempfile.mkstemp(
                    prefix="extract_folder_content_",
                    suffix=".md",
                    text=True,
                )
                os.close(fd)

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
                    raw_lightonocr_response = content_result.get("raw_response")
                else:
                    content = content_result
                    raw_lightonocr_response = None

                if raw_lightonocr_response is not None:
                    raw_lightonocr_entries.append(
                        {
                            "filename": os.path.basename(current_image_path),
                            "response": raw_lightonocr_response,
                        }
                    )

                content_block = f"### {os.path.basename(current_image_path)}\n\n{content}"
                if folder_content_spool_path:
                    with open(folder_content_spool_path, "a", encoding="utf-8") as f:
                        if os.path.getsize(folder_content_spool_path) > 0:
                            f.write("\n\n")
                        f.write(content_block)

                preview_block = (
                    f"\n\n{content_block}" if content_preview_parts else content_block
                )
                remaining_preview = content_preview_limit - content_preview_chars
                if remaining_preview > 0:
                    content_preview_parts.append(preview_block[:remaining_preview])
                    content_preview_chars += min(len(preview_block), remaining_preview)
                    if len(preview_block) > remaining_preview:
                        content_preview_truncated = True
                else:
                    content_preview_truncated = True

                parsed = None
                if output_format == "json":
                    try:
                        parsed = json.loads(_clean_json_string(content))
                    except json.JSONDecodeError:
                        parsed = None

                parsed_lv1 = None
                if parsed is not None:
                    parsed_lv1 = json.loads(json.dumps(parsed, ensure_ascii=False))
                    combined_lv1_payloads.append(
                        {
                            "filename": os.path.basename(current_image_path),
                            "data": parsed_lv1,
                        }
                    )

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

                current_lv1_rows: list[dict] = []
                if parsed_lv1 is not None:
                    raw_rows = _extract_records_for_mapping(parsed_lv1)
                    if isinstance(raw_rows, list):
                        current_lv1_rows = [
                            row for row in raw_rows if isinstance(row, dict)
                        ]
                    elif isinstance(raw_rows, dict):
                        current_lv1_rows = [raw_rows]
                    combined_lv1_rows.extend(current_lv1_rows)

                current_template_rows: list[dict] = []
                if parsed is not None:
                    mapped_rows = _extract_records_for_mapping(parsed)
                    if isinstance(mapped_rows, list):
                        current_template_rows = [
                            row for row in mapped_rows if isinstance(row, dict)
                        ]
                    elif isinstance(mapped_rows, dict):
                        current_template_rows = [mapped_rows]

                    combined_template_rows.extend(current_template_rows)

                ocr_text_preview, ocr_text_truncated = _truncate_text(
                    content, per_file_ocr_preview_limit
                )
                result_entry = (
                    {
                        "filename": os.path.basename(current_image_path),
                        "ocr_text": ocr_text_preview,
                        "ocr_text_truncated": ocr_text_truncated,
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
                folder_results.append(result_entry)

                if per_image_dir and output_format == "json":
                    image_filename = os.path.basename(current_image_path)
                    image_base = _safe_name(os.path.splitext(image_filename)[0])
                    image_slug = f"{index:05d}_{image_base}"
                    image_json_path = os.path.join(per_image_dir, f"{image_slug}.json")
                    image_raw_path = os.path.join(
                        per_image_dir, f"{image_slug}_raw_lightonocr.json"
                    )
                    image_lv1_json_path = os.path.join(
                        per_image_dir, f"{image_slug}_lv1.json"
                    )
                    image_lv1_path = os.path.join(
                        per_image_dir, f"excel_{image_slug}_lv1.xlsx"
                    )
                    image_template_path = os.path.join(
                        per_image_dir, f"excel_{image_slug}_template.xlsx"
                    )

                    per_image_payload = (
                        parsed
                        if parsed is not None
                        else {
                            "filename": image_filename,
                            "ocr_text": content,
                            "error": "Could not parse OCR response as JSON",
                        }
                    )
                    with open(image_json_path, "w", encoding="utf-8") as f:
                        json.dump(per_image_payload, f, ensure_ascii=False, indent=2)

                    artifact_entry: dict[str, Any] = {
                        "filename": image_filename,
                        "stem": image_slug,
                        "json": image_json_path,
                        "template_json": image_json_path,
                    }
                    if raw_lightonocr_response is not None:
                        artifact_entry["raw_lightonocr_json"] = _save_json_artifact(
                            raw_lightonocr_response, image_raw_path
                        )
                    if parsed_lv1 is not None:
                        artifact_entry["lv1_json"] = _save_json_artifact(
                            parsed_lv1, image_lv1_json_path
                        )

                    if parsed_lv1 is not None:
                        artifact_entry["excel_lv1"] = (
                            _save_combined_excel(current_lv1_rows, image_lv1_path)
                            if current_lv1_rows
                            else _save_excel_from_json(parsed_lv1, image_lv1_path)
                        )

                    if parsed is not None:
                        if template_id != "default" and current_template_rows:
                            from app.services.excel_writer import (
                                write_rows_to_template,
                                get_template_excel_path,
                                get_template_sheet_name,
                            )

                            tmpl_file = get_template_excel_path(template_id)
                            tmpl_sheet = get_template_sheet_name(template_id)
                            if tmpl_file:
                                artifact_entry["excel_template"] = (
                                    write_rows_to_template(
                                        rows=current_template_rows,
                                        template_path=tmpl_file,
                                        output_path=image_template_path,
                                        sheet_name=tmpl_sheet,
                                    )
                                )
                            else:
                                artifact_entry["excel_template"] = _save_combined_excel(
                                    current_template_rows, image_template_path
                                )
                        elif current_template_rows:
                            artifact_entry["excel_template"] = _save_combined_excel(
                                current_template_rows, image_template_path
                            )
                        else:
                            artifact_entry["excel_template"] = _save_excel_from_json(
                                parsed, image_template_path
                            )

                    per_image_artifacts.append(
                        {
                            key: value
                            for key, value in artifact_entry.items()
                            if value is not None
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
                if folder_save_context is None:
                    raise RuntimeError("Folder save context was not initialized")
                saved_path = folder_save_context["saved_path"]
                raw_lightonocr_path = folder_save_context["raw_lightonocr_path"]
                lv1_json_path = folder_save_context["lv1_json_path"]
                excel_lv1_path = folder_save_context["excel_lv1_path"]
                excel_template_path = folder_save_context["excel_template_path"]

                if output_format == "json":
                    with open(saved_path, "w", encoding="utf-8") as f:
                        json.dump(folder_results, f, ensure_ascii=False, indent=2)
                    if raw_lightonocr_entries:
                        saved_raw_lightonocr_json = _save_json_artifact(
                            raw_lightonocr_entries, raw_lightonocr_path
                        )
                    if combined_lv1_payloads:
                        saved_lv1_json = _save_json_artifact(
                            combined_lv1_payloads, lv1_json_path
                        )

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
                    if per_image_artifacts:
                        manifest = []
                        for artifact in per_image_artifacts:
                            manifest.append(
                                {
                                    "filename": artifact.get("filename"),
                                    "json": (
                                        os.path.basename(artifact["json"])
                                        if artifact.get("json")
                                        else None
                                    ),
                                    "raw_lightonocr_json": (
                                        os.path.basename(
                                            artifact["raw_lightonocr_json"]
                                        )
                                        if artifact.get("raw_lightonocr_json")
                                        else None
                                    ),
                                    "lv1_json": (
                                        os.path.basename(artifact["lv1_json"])
                                        if artifact.get("lv1_json")
                                        else None
                                    ),
                                    "template_json": (
                                        os.path.basename(artifact["template_json"])
                                        if artifact.get("template_json")
                                        else None
                                    ),
                                    "excel_lv1": (
                                        os.path.basename(artifact["excel_lv1"])
                                        if artifact.get("excel_lv1")
                                        else None
                                    ),
                                    "excel_template": (
                                        os.path.basename(artifact["excel_template"])
                                        if artifact.get("excel_template")
                                        else None
                                    ),
                                }
                            )
                        manifest_path = os.path.join(per_image_dir, "manifest.json")
                        with open(manifest_path, "w", encoding="utf-8") as f:
                            json.dump(manifest, f, ensure_ascii=False, indent=2)

                        saved_per_image_zip = folder_save_context[
                            "per_image_zip_path"
                        ]
                        with zipfile.ZipFile(
                            saved_per_image_zip, "w", compression=zipfile.ZIP_DEFLATED
                        ) as zip_file:
                            zip_file.write(manifest_path, "manifest.json")
                            for artifact in per_image_artifacts:
                                stem = artifact.get("stem") or "image"
                                for key in (
                                    "raw_lightonocr_json",
                                    "lv1_json",
                                    "template_json",
                                    "excel_lv1",
                                    "excel_template",
                                ):
                                    file_path = artifact.get(key)
                                    if file_path and os.path.exists(file_path):
                                        zip_file.write(
                                            file_path,
                                            f"{stem}/{os.path.basename(file_path)}",
                                        )
                else:
                    if folder_content_spool_path and os.path.exists(
                        folder_content_spool_path
                    ):
                        shutil.copyfile(folder_content_spool_path, saved_path)
                    else:
                        with open(saved_path, "w", encoding="utf-8") as f:
                            f.write("".join(content_preview_parts))

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
                "content": "".join(content_preview_parts),
                "content_truncated": content_preview_truncated,
                "saved_to": saved_path,
                "saved_excel": saved_excel,
                "saved_excel_lv1": saved_excel_lv1,
                "saved_excel_template": saved_excel_template,
                "saved_raw_lightonocr_json": saved_raw_lightonocr_json,
                "saved_lv1_json": saved_lv1_json,
                "saved_per_image_zip": saved_per_image_zip,
                "per_image_artifact_count": len(per_image_artifacts),
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
        raw_lightonocr_response = None

        if isinstance(content_result, dict):
            content = content_result.get("text", "")
            api_base_url = content_result.get("base_url", "http://localhost:8000")
            api_json_path = content_result.get("api_json_path")
            api_excel_path = content_result.get("api_excel_path")
            raw_lightonocr_response = content_result.get("raw_response")
        else:
            content = content_result

        # 4. Save to file if requested
        saved_path = None
        saved_excel = None
        saved_excel_lv1 = None
        saved_excel_template = None
        saved_raw_lightonocr_json = None
        saved_lv1_json = None
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
            if task_id != "unknown":
                base_slug = "_".join(
                    [
                        base_slug,
                        _safe_name(template_id or "default"),
                        _safe_name(task_id.split("-")[0]),
                    ]
                )
            elif template_id and template_id != "default":
                base_slug = f"{base_slug}_{_safe_name(template_id)}"
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
            raw_lightonocr_path = os.path.join(
                dated_output_dir, f"{base_slug}_raw_lightonocr.json"
            )
            lv1_json_path = os.path.join(dated_output_dir, f"{base_slug}_lv1.json")
            excel_name_prefix = f"excel_{base_slug}"
            excel_lv1_path = os.path.join(
                dated_output_dir, f"{excel_name_prefix}_lv1.xlsx"
            )
            excel_template_path = os.path.join(
                dated_output_dir, f"{excel_name_prefix}_template.xlsx"
            )

            # Nếu API có file JSON chuẩn và định dạng yêu cầu là json, thử tải về thay vì ghi text chay
            downloaded_json = False
            if output_format == "json" and raw_lightonocr_response is not None:
                saved_raw_lightonocr_json = _save_json_artifact(
                    raw_lightonocr_response, raw_lightonocr_path
                )
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
                    if saved_raw_lightonocr_json is None:
                        try:
                            with open(saved_path, "r", encoding="utf-8") as f:
                                downloaded_raw = json.load(f)
                            saved_raw_lightonocr_json = _save_json_artifact(
                                downloaded_raw, raw_lightonocr_path
                            )
                        except Exception:
                            pass
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
                    saved_lv1_json = _save_json_artifact(parsed_lv1, lv1_json_path)

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
            "saved_raw_lightonocr_json": saved_raw_lightonocr_json,
            "saved_lv1_json": saved_lv1_json,
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
        if folder_content_spool_path and os.path.exists(folder_content_spool_path):
            try:
                os.remove(folder_content_spool_path)
            except Exception:
                pass
        # Cleanup uploaded file if needed?
        # For now, let's keep it or manage cleanup policy separately
        # os.remove(image_path)
        pass
