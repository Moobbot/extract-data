"""
app/services/providers/factory.py

AIProviderFactory — tạo provider phù hợp theo tên agent và config.
Hỗ trợ: gemini, openai, openai_compatible, local_http, lightonocr,
        và agent động từ env (AGENT_<NAME>_TYPE, ...).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.core.config import settings
from .base import AIProvider
from .gemini import GeminiProvider
from .lightonocr import LightOnOCRProvider
from .local_http import LocalHTTPProvider
from .openai_provider import OpenAIProvider


class AIProviderFactory:
    """Factory tạo AIProvider theo tên agent và config runtime."""

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _is_localhost_endpoint(endpoint: str) -> bool:
        """Kiểm tra endpoint có trỏ về localhost không."""
        if not endpoint:
            return False
        try:
            host = (urlparse(endpoint).hostname or "").lower()
            return host in {"localhost", "127.0.0.1", "0.0.0.0"}
        except Exception:
            return False

    @staticmethod
    def _resolve_local_http_endpoint(config_endpoint: Optional[str]) -> Optional[str]:
        """Chọn endpoint phù hợp giữa config và env var.

        Trong Docker, ui-config thường lưu localhost — không hợp lệ bên trong
        container. Ưu tiên LOCAL_HTTP_BASE_URL từ env trong trường hợp đó.
        """
        endpoint = (config_endpoint or "").strip()
        env_endpoint = os.getenv("LOCAL_HTTP_BASE_URL", "").strip()

        if env_endpoint and (
            not endpoint or AIProviderFactory._is_localhost_endpoint(endpoint)
        ):
            return env_endpoint

        return endpoint or env_endpoint or None

    @staticmethod
    def extract_text_from_response(parsed: Any) -> str:
        """Trích xuất text từ JSON response (hỗ trợ nhiều format API khác nhau)."""
        if isinstance(parsed, dict):
            for key in ("content", "text", "result", "markdown", "output"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        if isinstance(parsed, list):
            return json.dumps(parsed, ensure_ascii=False)
        return str(parsed)

    # ── Builders ─────────────────────────────────────────────────────────────

    @staticmethod
    def _build_gemini(config: Dict[str, Any]) -> AIProvider:
        api_key = config.get("api_key") or settings.GOOGLE_API_KEY
        model = config.get("model")
        return GeminiProvider(
            api_key=api_key,
            model_candidates=[model] if model else None,
        )

    @staticmethod
    def _build_openai(config: Dict[str, Any]) -> AIProvider:
        api_key = config.get("api_key") or settings.OPENAI_API_KEY
        model = config.get("model") or settings.DEFAULT_OPENAI_MODEL
        base_url = config.get("base_url") or settings.DEFAULT_OPENAI_BASE_URL or None
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)

    @staticmethod
    def _build_openai_compatible(config: Dict[str, Any]) -> AIProvider:
        api_key = config.get("api_key")
        model = config.get("model")
        base_url = config.get("base_url")

        missing = [k for k in ("api_key", "model", "base_url") if not config.get(k)]
        if missing:
            raise ValueError(
                f"[openai_compatible] Thiếu các trường: {', '.join(missing)}.\n"
                "Cấu hình đầy đủ trong ui-config.json hoặc env AGENT_<NAME>_*."
            )
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)

    @staticmethod
    def _build_local_http(config: Dict[str, Any]) -> AIProvider:
        endpoint = AIProviderFactory._resolve_local_http_endpoint(config.get("base_url"))
        return LocalHTTPProvider(
            endpoint=endpoint,
            api_key=config.get("api_key"),
            model=config.get("model"),
        )

    @staticmethod
    def _build_lightonocr(config: Dict[str, Any]) -> AIProvider:
        endpoint = AIProviderFactory._resolve_local_http_endpoint(config.get("base_url"))
        return LightOnOCRProvider(endpoint=endpoint)

    # ── Registry ─────────────────────────────────────────────────────────────

    _BUILDERS = {
        "gemini": _build_gemini.__func__,           # type: ignore[attr-defined]
        "openai": _build_openai.__func__,           # type: ignore[attr-defined]
        "openai_compatible": _build_openai_compatible.__func__,  # type: ignore[attr-defined]
        "local_http": _build_local_http.__func__,   # type: ignore[attr-defined]
        "lightonocr": _build_lightonocr.__func__,   # type: ignore[attr-defined]
    }

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def list_available_agents() -> List[Dict[str, Any]]:
        """Liệt kê tất cả agent có sẵn (builtin + động từ env)."""
        builtin = [
            {"name": "gemini",            "type": "gemini",           "source": "builtin", "requires": ["api_key"]},
            {"name": "openai",            "type": "openai",           "source": "builtin", "requires": ["api_key"]},
            {"name": "local_http",        "type": "local_http",       "source": "builtin", "requires": ["base_url"]},
            {"name": "openai_compatible", "type": "openai_compatible","source": "builtin", "requires": ["api_key", "base_url", "model"]},
            {"name": "lightonocr",        "type": "lightonocr",       "source": "builtin", "requires": ["base_url"]},
        ]

        env_agents = []
        for key, value in os.environ.items():
            if not (key.startswith("AGENT_") and key.endswith("_TYPE")):
                continue
            raw_name = key[len("AGENT_"):-len("_TYPE")]
            env_agents.append({
                "name": raw_name.lower(),
                "type": value.strip().lower(),
                "source": "env",
                "has_api_key": bool(os.getenv(f"AGENT_{raw_name}_API_KEY")),
                "has_base_url": bool(os.getenv(f"AGENT_{raw_name}_BASE_URL")),
                "has_model": bool(os.getenv(f"AGENT_{raw_name}_MODEL")),
            })

        env_agents.sort(key=lambda a: a["name"])
        return builtin + env_agents

    @staticmethod
    def _build_from_env(agent_name: str) -> Optional[AIProvider]:
        """Tạo provider từ env vars AGENT_<NAME>_TYPE / _API_KEY / _BASE_URL / _MODEL."""
        env_key = agent_name.upper().replace("-", "_")
        agent_type = os.getenv(f"AGENT_{env_key}_TYPE", "").strip().lower()
        if not agent_type:
            return None

        config = {
            "api_key":  os.getenv(f"AGENT_{env_key}_API_KEY", ""),
            "base_url": os.getenv(f"AGENT_{env_key}_BASE_URL", ""),
            "model":    os.getenv(f"AGENT_{env_key}_MODEL", ""),
        }

        builder = AIProviderFactory._BUILDERS.get(agent_type)
        if not builder:
            raise ValueError(
                f"Env agent '{agent_name}' có type không hỗ trợ: {agent_type}.\n"
                f"Hỗ trợ: {', '.join(AIProviderFactory._BUILDERS)}"
            )
        return builder(config)

    @staticmethod
    def get_provider(
        agent_name: str,
        agent_config: Optional[Dict[str, Any]] = None,
    ) -> AIProvider:
        """Tạo AIProvider phù hợp theo tên agent và config runtime.

        Args:
            agent_name: Tên agent (gemini, openai, lightonocr, ...).
            agent_config: Config runtime (api_key, base_url, model, ...).

        Returns:
            Instance của AIProvider tương ứng.

        Raises:
            ValueError: Khi agent không được hỗ trợ hoặc thiếu config bắt buộc.
        """
        normalized = (agent_name or settings.DEFAULT_PROVIDER).strip().lower()
        config = agent_config or {}

        # 1. Builtin providers
        builder = AIProviderFactory._BUILDERS.get(normalized)
        if builder:
            return builder(config)

        # 2. Env-configured providers (AGENT_<NAME>_TYPE)
        env_provider = AIProviderFactory._build_from_env(normalized)
        if env_provider:
            return env_provider

        # 3. Fallback: OpenAI-compatible nếu có đủ runtime config
        if all(config.get(k) for k in ("api_key", "base_url", "model")):
            return AIProviderFactory._build_openai_compatible(config)

        raise ValueError(
            f"Agent không được hỗ trợ: '{agent_name}'.\n"
            f"Builtin: {', '.join(AIProviderFactory._BUILDERS)}.\n"
            "Hoặc thêm env AGENT_<NAME>_TYPE=<type> để đăng ký agent động."
        )
