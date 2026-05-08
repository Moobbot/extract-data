import json
import zipfile
from pathlib import Path

from app.api.routes import _compact_task_result


def test_compact_task_result_truncates_large_content(monkeypatch):
    monkeypatch.setenv("TASK_RESULT_CONTENT_PREVIEW_CHARS", "20")

    result = _compact_task_result(
        {
            "status": "success",
            "filename": "sample.jpg",
            "content": "x" * 100,
            "saved_to": "/tmp/sample.json",
            "large_internal_value": "y" * 100,
        }
    )

    assert result["status"] == "success"
    assert result["filename"] == "sample.jpg"
    assert result["saved_to"] == "/tmp/sample.json"
    assert result["content"].startswith("x" * 20)
    assert result["content_truncated"] is True
    assert "large_internal_value" not in result


def test_process_image_task_folder_returns_preview_and_truncated_ocr(
    monkeypatch, tmp_path
):
    from app.core import config as core_config
    from app.core import db
    from app.services import tasks

    class FakeProvider:
        def generate_content(self, image_path: str, prompt: str) -> dict:
            raw_response = {
                "filename": Path(image_path).name,
                "data": {"rows": [{"name": Path(image_path).stem, "score": 10}]},
                "raw_text": "raw-lightonocr",
            }
            return {
                "text": json.dumps(
                    raw_response["data"],
                    ensure_ascii=False,
                ),
                "raw_response": raw_response,
                "base_url": "http://127.0.0.1:7861",
                "api_json_path": None,
                "api_excel_path": None,
            }

    batch_dir = tmp_path / "batch"
    batch_dir.mkdir()
    (batch_dir / "a.jpg").write_bytes(b"fake")
    (batch_dir / "b.jpg").write_bytes(b"fake")

    output_dir = tmp_path / "outputs"
    monkeypatch.setattr(core_config.settings, "OUTPUT_DIR", str(output_dir))
    monkeypatch.setenv("TASK_RESULT_CONTENT_PREVIEW_CHARS", "60")
    monkeypatch.setenv("TASK_RESULT_OCR_TEXT_PREVIEW_CHARS", "10")
    monkeypatch.setattr(
        tasks.AIProviderFactory, "get_provider", lambda *a, **k: FakeProvider()
    )
    monkeypatch.setattr(tasks.PromptManager, "get_prompt", lambda fmt: "prompt")
    monkeypatch.setattr(db, "update_task_status", lambda *a, **k: None)

    result = tasks.process_image_task(
        str(batch_dir),
        agent="lightonocr",
        output_format="json",
        save_to_file=True,
        task_id="test-task",
    )

    assert result["status"] == "success"
    assert result["content_truncated"] is True
    assert len(result["content"]) <= 60
    assert result["saved_to"]
    assert result["saved_per_image_zip"]
    assert result["saved_raw_lightonocr_json"]
    assert result["saved_lv1_json"]
    assert result["per_image_artifact_count"] == 2

    saved_payload = json.loads(Path(result["saved_to"]).read_text())
    assert saved_payload
    assert all(len(item["ocr_text"]) <= 10 for item in saved_payload)
    assert all(item["ocr_text_truncated"] is True for item in saved_payload)

    with zipfile.ZipFile(result["saved_per_image_zip"]) as zip_file:
        names = zip_file.namelist()
    assert "manifest.json" in names
    assert len([name for name in names if name.endswith(".json")]) == 7
    assert any(name.endswith("_raw_lightonocr.json") for name in names)
    assert any(name.endswith("_lv1.json") for name in names)


def test_process_image_task_single_outputs_are_task_unique(monkeypatch, tmp_path):
    from app.core import config as core_config
    from app.core import db
    from app.services import tasks

    class FakeProvider:
        def generate_content(self, image_path: str, prompt: str) -> dict:
            raw_response = {
                "data": {"rows": [{"STT": "1", "Họ và tên": "Nguyen Van A"}]},
                "raw_text": "raw-lightonocr",
            }
            return {
                "text": json.dumps(raw_response["data"], ensure_ascii=False),
                "raw_response": raw_response,
                "base_url": "http://127.0.0.1:7861",
                "api_json_path": None,
                "api_excel_path": None,
            }

    image_file = tmp_path / "Trang000018.jpg"
    image_file.write_bytes(b"fake")
    output_dir = tmp_path / "outputs"

    monkeypatch.setattr(core_config.settings, "OUTPUT_DIR", str(output_dir))
    monkeypatch.setattr(
        tasks.AIProviderFactory, "get_provider", lambda *a, **k: FakeProvider()
    )
    monkeypatch.setattr(tasks.PromptManager, "get_prompt", lambda fmt: "prompt")
    monkeypatch.setattr(db, "update_task_status", lambda *a, **k: None)

    default_result = tasks.process_image_task(
        str(image_file),
        agent="lightonocr",
        output_format="json",
        save_to_file=True,
        template_id="default",
        source_filename=image_file.name,
        task_id="11111111-aaaa-bbbb-cccc-111111111111",
    )
    template_result = tasks.process_image_task(
        str(image_file),
        agent="lightonocr",
        output_format="json",
        save_to_file=True,
        template_id="van_bang_dai_hoc",
        source_filename=image_file.name,
        task_id="22222222-aaaa-bbbb-cccc-222222222222",
    )

    default_path = Path(default_result["saved_to"])
    template_path = Path(template_result["saved_to"])
    assert default_path != template_path
    assert default_path.name == "Trang000018_default_11111111.json"
    assert template_path.name == "Trang000018_van_bang_dai_hoc_22222222.json"
    assert default_path.exists()
    assert template_path.exists()
    assert Path(default_result["saved_raw_lightonocr_json"]).exists()
    assert Path(template_result["saved_raw_lightonocr_json"]).exists()
