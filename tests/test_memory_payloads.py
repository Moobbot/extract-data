import json
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
        def generate_content(self, image_path: str, prompt: str) -> str:
            return json.dumps(
                {"tables": [], "text_lines": [], "kv_pairs": {}, "raw": "x" * 80},
                ensure_ascii=False,
            )

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

    saved_payload = json.loads(Path(result["saved_to"]).read_text())
    assert saved_payload
    assert all(len(item["ocr_text"]) <= 10 for item in saved_payload)
    assert all(item["ocr_text_truncated"] is True for item in saved_payload)
