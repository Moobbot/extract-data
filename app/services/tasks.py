from app.core.celery_app import celery_app
from app.services.ai_providers import AIProviderFactory
from app.services.prompt_manager import PromptManager
import os
import json
from typing import Any, Dict, Optional

import pandas as pd


@celery_app.task(bind=True)
def process_image_task(
    self,
    image_path: str,
    agent: str,
    output_format: str,
    save_to_file: bool = False,
    agent_config: Optional[Dict[str, Any]] = None,
):
    """
    Background task to process an image.
    """

    def _clean_json_string(raw_text: str) -> str:
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _save_excel_from_json(data: Any, saved_path: str) -> Optional[str]:
        excel_path = os.path.splitext(saved_path)[0] + ".xlsx"

        try:
            sheets = {}

            if isinstance(data, list):
                sheets["Sheet1"] = pd.DataFrame(data)
            elif isinstance(data, dict):
                found_list = False
                for key, value in data.items():
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        sheet_name = str(key)[:31]
                        sheets[sheet_name] = pd.DataFrame(value)
                        found_list = True

                if not found_list:
                    sheets["Sheet1"] = pd.DataFrame([data])
            else:
                sheets["Sheet1"] = pd.DataFrame([{"result": data}])

            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                for sheet_name, frame in sheets.items():
                    frame.to_excel(writer, sheet_name=sheet_name, index=False)

            return excel_path
        except Exception:
            return None

    try:
        self.update_state(state="PROGRESS", meta={"message": "Processing started"})

        # 1. Get Provider
        try:
            ai_provider = AIProviderFactory.get_provider(agent, agent_config)
        except ValueError as e:
            from app.core.db import update_task_status
            update_task_status(task_id, "failed", error=str(e))
            return {"error": str(e), "status": "failed"}

        # 2. Get Prompt
        prompt = PromptManager.get_prompt(output_format)

        self.update_state(
            state="PROGRESS", meta={"message": "Generating content with AI"}
        )

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
        if save_to_file:
            from app.core.config import settings
            import requests

            base_name = os.path.splitext(os.path.basename(image_path))[0]
            ext = "md" if output_format == "markdown" else "json"
            output_filename = f"{base_name}.{ext}"
            saved_path = os.path.join(settings.OUTPUT_DIR, output_filename)

            # Nếu API có file JSON chuẩn và định dạng yêu cầu là json, thử tải về thay vì ghi text chay
            downloaded_json = False
            if output_format == "json" and api_json_path and api_base_url:
                try:
                    res = requests.post(f"{api_base_url}/download", json={"path": api_json_path}, timeout=60)
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

            # Xử lý Excel
            if output_format == "json":
                # Thử tải Excel xịn từ API trước
                if api_excel_path and api_base_url:
                    excel_out = os.path.join(settings.OUTPUT_DIR, f"{base_name}.xlsx")
                    try:
                        res = requests.post(f"{api_base_url}/download", json={"path": api_excel_path}, timeout=60)
                        res.raise_for_status()
                        with open(excel_out, "wb") as f:
                            f.write(res.content)
                        saved_excel = excel_out
                    except Exception:
                        pass
                
                # Nếu API không có excel hoặc lỗi tải, thì tự generate
                if not saved_excel:
                    try:
                        parsed = json.loads(_clean_json_string(content))
                    except json.JSONDecodeError:
                        parsed = None

                    if parsed is not None:
                        saved_excel = _save_excel_from_json(parsed, saved_path)

        from app.core.db import update_task_status
        update_task_status(task_id, "success", json_path=saved_path, excel_path=saved_excel)

        return {
            "status": "success",
            "agent": agent,
            "provider": agent,
            "format": output_format,
            "filename": os.path.basename(image_path),
            "content": content,
            "saved_to": saved_path,
            "saved_excel": saved_excel,
            "api_base_url": api_base_url,
            "api_json_path": api_json_path,
            "api_excel_path": api_excel_path,
        }

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        from app.core.db import update_task_status
        update_task_status(task_id, "failed", error=str(e))
        raise e
    finally:
        # Cleanup uploaded file if needed?
        # For now, let's keep it or manage cleanup policy separately
        # os.remove(image_path)
        pass
