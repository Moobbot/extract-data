from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


CONFIG_PATH = Path(__file__).resolve().parents[2] / "ui-config.json"


def default_ui_config() -> Dict[str, Any]:
    return {
        "active_profile_id": "lightonocr-2-1b",
        "profiles": [
            {
                "id": "lightonocr-2-1b",
                "label": "LightOnOCR-2-1B",
                "agent": "local_http",
                "model": "LightOnOCR-2-1B",
                "base_url": "http://127.0.0.1:7860/ocr",
                "api_key": "",
                "output_format": "markdown",
                "save_to_file": False,
                "description": "Preset chạy LightOnOCR như một API local_http.",
            },
            {
                "id": "gemini-flash",
                "label": "Gemini 2.5 Flash",
                "agent": "gemini",
                "model": "gemini-2.5-flash",
                "base_url": "",
                "api_key": "",
                "output_format": "markdown",
                "save_to_file": False,
                "description": "Preset Gemini cho OCR tổng quát.",
            },
            {
                "id": "openai-gpt4o",
                "label": "OpenAI GPT-4o",
                "agent": "openai",
                "model": "gpt-4o",
                "base_url": "",
                "api_key": "",
                "output_format": "markdown",
                "save_to_file": False,
                "description": "Preset OpenAI cho trường hợp cần model đa phương thức.",
            },
        ],
    }


def _merge_profile(
    default_profile: Dict[str, Any], candidate: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(default_profile)
    for key, value in candidate.items():
        if key in merged:
            merged[key] = value
    return merged


def normalize_ui_config(raw_config: Dict[str, Any] | None) -> Dict[str, Any]:
    defaults = default_ui_config()
    if not isinstance(raw_config, dict):
        return defaults

    normalized = dict(defaults)
    normalized["active_profile_id"] = str(
        raw_config.get("active_profile_id") or defaults["active_profile_id"]
    )

    raw_profiles = raw_config.get("profiles")
    if isinstance(raw_profiles, list) and raw_profiles:
        default_profiles = {item["id"]: item for item in defaults["profiles"]}
        normalized_profiles = []
        for profile in raw_profiles:
            if not isinstance(profile, dict):
                continue
            profile_id = str(profile.get("id") or "").strip()
            if not profile_id:
                continue
            base_profile = default_profiles.get(profile_id, defaults["profiles"][0])
            normalized_profiles.append(_merge_profile(base_profile, profile))
        if normalized_profiles:
            normalized["profiles"] = normalized_profiles

    active_profile_exists = any(
        profile.get("id") == normalized["active_profile_id"]
        for profile in normalized["profiles"]
    )
    if not active_profile_exists and normalized["profiles"]:
        normalized["active_profile_id"] = normalized["profiles"][0]["id"]

    return normalized


def load_ui_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return default_ui_config()

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            raw_config = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return default_ui_config()

    return normalize_ui_config(raw_config)


def save_ui_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_ui_config(config)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(normalized, config_file, ensure_ascii=False, indent=2)
        config_file.write("\n")
    return normalized


def get_active_profile(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    current_config = normalize_ui_config(config or load_ui_config())
    active_id = current_config["active_profile_id"]
    for profile in current_config["profiles"]:
        if profile.get("id") == active_id:
            return profile
    return current_config["profiles"][0]
