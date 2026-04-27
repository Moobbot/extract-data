import base64
import json
from types import SimpleNamespace
import importlib

import pytest

from app.main import app
from app.services.ai_providers import AIProviderFactory


def get_test_client():
    try:
        module = importlib.import_module("fastapi.testclient")
    except ModuleNotFoundError:
        pytest.skip("fastapi test dependencies are not installed")
    return module.TestClient(app)


class DummyDelay:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(id="task-123")


class DummyProvider:
    def generate_content(self, image_path: str, prompt: str) -> str:
        return "ok"


def test_quick_ui_endpoint_served():
    client = get_test_client()
    response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Extract PDF - TMU Quick UI" in response.text
    assert "Download JSON" in response.text
    assert "Download Excel" in response.text
    assert "Copy Content" in response.text
    assert "Clear" in response.text


def test_settings_ui_endpoint_served():
    client = get_test_client()
    response = client.get("/ui/settings")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Settings" in response.text
    assert "ui-config.json" in response.text


def test_ui_config_roundtrip(monkeypatch, tmp_path):
    from app.core import ui_config

    monkeypatch.setattr(ui_config, "CONFIG_PATH", tmp_path / "ui-config.json")

    client = get_test_client()
    response = client.get("/api/v1/ui-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_profile_id"] == "lightonocr-2-1b"
    lighton_profile = next(
        profile
        for profile in payload["profiles"]
        if profile["label"] == "LightOnOCR-2-1B"
    )
    assert lighton_profile["base_url"] == "http://127.0.0.1:7860/ocr"

    payload["active_profile_id"] = "gemini-flash"
    save_response = client.put("/api/v1/ui-config", json=payload)

    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["active_profile_id"] == "gemini-flash"
    assert (tmp_path / "ui-config.json").exists()


def test_extract_form_builtin_agent_dispatch(monkeypatch, tmp_path):
    from app.api import routes

    client = get_test_client()
    dummy_delay = DummyDelay()
    monkeypatch.setattr(routes.process_image_task, "delay", dummy_delay)

    image_file = tmp_path / "sample.jpg"
    image_file.write_bytes(b"fake-image-content")

    with image_file.open("rb") as f:
        response = client.post(
            "/api/v1/extract",
            files={"file": ("sample.jpg", f, "image/jpeg")},
            data={"agent": "gemini", "output_format": "markdown"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert len(dummy_delay.calls) == 1

    args, _ = dummy_delay.calls[0]
    assert args[1] == "gemini"
    assert args[2] == "markdown"
    assert args[4] == {}


def test_extract_json_openai_compatible_runtime_dispatch(monkeypatch):
    from app.api import routes

    client = get_test_client()
    dummy_delay = DummyDelay()
    monkeypatch.setattr(routes.process_image_task, "delay", dummy_delay)

    payload = {
        "image_base64": base64.b64encode(b"inline-image").decode("utf-8"),
        "filename": "inline.jpg",
        "agent": "openai_compatible",
        "output_format": "json",
        "options": {
            "model": "local-vlm",
            "base_url": "http://127.0.0.1:8001/v1",
            "api_key": "local-key",
        },
    }

    response = client.post("/api/v1/extract/json", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert len(dummy_delay.calls) == 1

    args, _ = dummy_delay.calls[0]
    assert args[1] == "openai_compatible"
    assert args[2] == "json"
    assert args[4] == {
        "model": "local-vlm",
        "base_url": "http://127.0.0.1:8001/v1",
        "api_key": "local-key",
    }


def test_env_configured_agent_flow(monkeypatch):
    client = get_test_client()
    monkeypatch.setenv("AGENT_QWEN_TYPE", "openai_compatible")
    monkeypatch.setenv("AGENT_QWEN_API_KEY", "env-key")
    monkeypatch.setenv("AGENT_QWEN_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENT_QWEN_MODEL", "qwen-vl")

    captured = {}

    def fake_builder(config):
        captured.update(config)
        return DummyProvider()

    monkeypatch.setattr(AIProviderFactory, "_build_openai_compatible", fake_builder)

    provider = AIProviderFactory.get_provider("qwen")

    assert isinstance(provider, DummyProvider)
    assert captured == {
        "api_key": "env-key",
        "base_url": "http://localhost:1234/v1",
        "model": "qwen-vl",
    }

    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    agent_names = [item["name"] for item in response.json()["agents"]]
    assert "qwen" in agent_names


def test_extract_json_local_http_dispatch(monkeypatch):
    from app.api import routes

    client = get_test_client()
    dummy_delay = DummyDelay()
    monkeypatch.setattr(routes.process_image_task, "delay", dummy_delay)

    payload = {
        "image_base64": base64.b64encode(b"inline-image").decode("utf-8"),
        "filename": "inline.jpg",
        "agent": "local_http",
        "output_format": "markdown",
        "options": {
            "base_url": "http://127.0.0.1:8080/ocr",
            "api_key": "local-token",
        },
    }

    response = client.post("/api/v1/extract/json", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert len(dummy_delay.calls) == 1

    args, _ = dummy_delay.calls[0]
    assert args[1] == "local_http"
    assert args[4] == {
        "base_url": "http://127.0.0.1:8080/ocr",
        "api_key": "local-token",
    }


def test_process_image_task_saves_excel_for_json(monkeypatch, tmp_path):
    from app.core import config as core_config
    from app.services import tasks

    monkeypatch.setattr(core_config.settings, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(
        tasks.AIProviderFactory, "get_provider", lambda *a, **k: DummyProvider()
    )
    monkeypatch.setattr(
        tasks.PromptManager, "get_prompt", lambda output_format: "prompt"
    )
    monkeypatch.setattr(
        DummyProvider,
        "generate_content",
        lambda self, image_path, prompt: json.dumps(
            [{"name": "Alice", "score": 10}, {"name": "Bob", "score": 20}],
            ensure_ascii=False,
        ),
    )
    monkeypatch.setattr(tasks.process_image_task, "update_state", lambda *a, **k: None)

    image_file = tmp_path / "sample.jpg"
    image_file.write_bytes(b"fake-image-content")

    result = tasks.process_image_task.__wrapped__(
        str(image_file),
        "gemini",
        "json",
        True,
        {},
    )

    assert result["status"] == "success"
    assert result["saved_to"].endswith(".json")
    assert result["saved_excel"] is not None
    assert result["saved_excel"].endswith(".xlsx")
    assert (tmp_path / "sample.json").exists()
    assert (tmp_path / "sample.xlsx").exists()


def test_download_task_artifact_endpoint(monkeypatch, tmp_path):
    from app.api import routes

    client = get_test_client()
    json_file = tmp_path / "sample.json"
    excel_file = tmp_path / "sample.xlsx"
    json_file.write_text('{"name": "Alice"}', encoding="utf-8")
    excel_file.write_bytes(b"fake-xlsx")

    monkeypatch.setattr(routes.settings, "OUTPUT_DIR", str(tmp_path))

    class DummyAsyncResult:
        state = "SUCCESS"
        result = {"saved_to": str(json_file), "saved_excel": str(excel_file)}

    monkeypatch.setattr(routes, "AsyncResult", lambda task_id: DummyAsyncResult())

    json_response = client.get("/api/v1/task-artifact/task-123/json")
    excel_response = client.get("/api/v1/task-artifact/task-123/excel")

    assert json_response.status_code == 200
    assert excel_response.status_code == 200
    assert json_response.headers["content-disposition"].endswith(
        'filename="sample.json"'
    )
    assert excel_response.headers["content-disposition"].endswith(
        'filename="sample.xlsx"'
    )
