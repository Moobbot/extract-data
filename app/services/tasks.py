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
            return {"error": str(e), "status": "failed"}

        # 2. Get Prompt
        prompt = PromptManager.get_prompt(output_format)

        self.update_state(
            state="PROGRESS", meta={"message": "Generating content with AI"}
        )

        # 3. Generate
        try:
            content = ai_provider.generate_content(image_path, prompt)
        except Exception as e:
            return {"error": f"AI generation failed: {str(e)}", "status": "failed"}

        # 4. Save to file if requested
        saved_path = None
        saved_excel = None
        if save_to_file:
            from app.core.config import settings

            base_name = os.path.splitext(os.path.basename(image_path))[0]
            ext = "md" if output_format == "markdown" else "json"
            output_filename = f"{base_name}.{ext}"
            saved_path = os.path.join(settings.OUTPUT_DIR, output_filename)

            with open(saved_path, "w", encoding="utf-8") as f:
                f.write(content)

            if output_format == "json":
                try:
                    parsed = json.loads(_clean_json_string(content))
                except json.JSONDecodeError:
                    parsed = None

                if parsed is not None:
                    saved_excel = _save_excel_from_json(parsed, saved_path)

        return {
            "status": "success",
            "agent": agent,
            "provider": agent,
            "format": output_format,
            "filename": os.path.basename(image_path),
            "content": content,
            "saved_to": saved_path,
            "saved_excel": saved_excel,
        }

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e
    finally:
        # Cleanup uploaded file if needed?
        # For now, let's keep it or manage cleanup policy separately
        # os.remove(image_path)
        pass
