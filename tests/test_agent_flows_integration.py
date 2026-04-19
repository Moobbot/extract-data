import base64
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
    assert "Extract PDF - Quick UI" in response.text


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
