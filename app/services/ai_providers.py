from app.core.interfaces import AIProvider
from app.core.config import settings
from app.services.image_processor import ImageProcessor
from google import genai
from PIL import Image
from typing import Any, Dict, List, Optional
import os
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model_candidates: Optional[List[str]] = None):
        if not api_key:
            raise ValueError("Google API Key is missing")
        self.client = genai.Client(api_key=api_key)
        self.model_candidates = model_candidates or [
            settings.DEFAULT_GEMINI_MODEL,
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-flash-latest",
            "gemini-2.5-pro",
            "gemini-pro-latest",
            "gemini-1.5-flash",
        ]

    def generate_content(self, image_path: str, prompt: str) -> str:
        img = Image.open(image_path)

        last_err = None
        for m in self.model_candidates:
            try:
                resp = self.client.models.generate_content(
                    model=m,
                    contents=[prompt, img],
                )
                return resp.text
            except Exception as e:
                last_err = e

        raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        if not OpenAI:
            raise ImportError("OpenAI module not installed")
        if not api_key:
            raise ValueError("OpenAI API Key is missing")
        self.model = model
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        self.client = OpenAI(**client_kwargs)

    def generate_content(self, image_path: str, prompt: str) -> str:
        base64_image = ImageProcessor.encode_image_base64(image_path)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI call failed: {e}")


class LocalHTTPProvider(AIProvider):
    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        if not endpoint:
            raise ValueError("Missing base_url/endpoint for local_http agent")

        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model

    def generate_content(self, image_path: str, prompt: str) -> str:
        base64_image = ImageProcessor.encode_image_base64(image_path)
        payload = {
            "image_base64": base64_image,
            "prompt": prompt,
        }
        if self.model:
            payload["model"] = self.model

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            url=self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=settings.DEFAULT_LOCAL_HTTP_TIMEOUT
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"local_http call failed with HTTP {e.code}: {body}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"local_http connection error: {e}") from e

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        return AIProviderFactory.extract_text_from_response(parsed)


class LightOnOCRProvider(AIProvider):
    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint or "http://localhost:8000/extract"

    def generate_content(self, image_path: str, prompt: str) -> str:
        import requests
        import os
        
        if not os.path.exists(image_path):
            raise RuntimeError(f"Image not found: {image_path}")

        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
            data = {
                "page_num": 1,
                "prompt": prompt,
                "temperature": 0.2,
                "max_tokens": 4096
            }
            
            try:
                response = requests.post(self.endpoint, files=files, data=data)
                response.raise_for_status()
                result = response.json()
                
                # Trả về dict chứa text và đường dẫn file
                base_url = self.endpoint.replace("/extract", "")
                
                text_content = ""
                if result.get("data") and isinstance(result["data"], dict) and result["data"]:
                    import json
                    text_content = json.dumps(result["data"], ensure_ascii=False, indent=2)
                else:
                    text_content = result.get("raw_text") or result.get("rendered_text") or str(result)
                    
                return {
                    "text": text_content,
                    "api_json_path": result.get("json_path"),
                    "api_excel_path": result.get("excel_path"),
                    "base_url": base_url
                }
            except requests.exceptions.RequestException as e:
                body = e.response.text if hasattr(e, 'response') and e.response else str(e)
                raise RuntimeError(f"LightOnOCR call failed: {body}")


class AIProviderFactory:
    @staticmethod
    def _is_localhost_endpoint(endpoint: str) -> bool:
        if not endpoint:
            return False
        try:
            parsed = urlparse(endpoint)
            host = (parsed.hostname or "").lower()
            return host in {"localhost", "127.0.0.1", "0.0.0.0"}
        except Exception:
            return False

    @staticmethod
    def _resolve_local_http_endpoint(config_endpoint: Optional[str]) -> Optional[str]:
        endpoint = (config_endpoint or "").strip()
        env_endpoint = os.getenv("LOCAL_HTTP_BASE_URL", "").strip()

        # In Docker, ui-config often stores localhost values that are invalid
        # from inside containers. Prefer env endpoint in that case.
        if env_endpoint and (not endpoint or AIProviderFactory._is_localhost_endpoint(endpoint)):
            return env_endpoint

        if endpoint:
            return endpoint

        if env_endpoint:
            return env_endpoint

        return None

    @staticmethod
    def extract_text_from_response(parsed: Any) -> str:
        if isinstance(parsed, dict):
            for key in (
                "content",
                "text",
                "result",
                "markdown",
                "output",
            ):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        if isinstance(parsed, list):
            return json.dumps(parsed, ensure_ascii=False)

        return str(parsed)

    @staticmethod
    def _build_gemini(config: Dict[str, Any]) -> AIProvider:
        api_key = config.get("api_key") or settings.GOOGLE_API_KEY
        model = config.get("model")
        model_candidates = [model] if model else None
        return GeminiProvider(api_key=api_key, model_candidates=model_candidates)

    @staticmethod
    def _build_openai(config: Dict[str, Any]) -> AIProvider:
        api_key = config.get("api_key") or settings.OPENAI_API_KEY
        model = config.get("model") or settings.DEFAULT_OPENAI_MODEL
        base_url = config.get("base_url") or settings.DEFAULT_OPENAI_BASE_URL or None
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)

    @staticmethod
    def _build_local_http(config: Dict[str, Any]) -> AIProvider:
        endpoint = AIProviderFactory._resolve_local_http_endpoint(config.get("base_url"))
        api_key = config.get("api_key")
        model = config.get("model")
        return LocalHTTPProvider(endpoint=endpoint, api_key=api_key, model=model)

    @staticmethod
    def _build_lightonocr(config: Dict[str, Any]) -> AIProvider:
        endpoint = AIProviderFactory._resolve_local_http_endpoint(config.get("base_url"))
        return LightOnOCRProvider(endpoint=endpoint)

    @staticmethod
    def list_available_agents() -> List[Dict[str, Any]]:
        builtin_agents = [
            {
                "name": "gemini",
                "type": "gemini",
                "source": "builtin",
                "requires": ["api_key"],
            },
            {
                "name": "openai",
                "type": "openai",
                "source": "builtin",
                "requires": ["api_key"],
            },
            {
                "name": "local_http",
                "type": "local_http",
                "source": "builtin",
                "requires": ["base_url"],
            },
            {
                "name": "openai_compatible",
                "type": "openai_compatible",
                "source": "builtin",
                "requires": ["api_key", "base_url", "model"],
            },
            {
                "name": "lightonocr",
                "type": "lightonocr",
                "source": "builtin",
                "requires": ["base_url"],
            },
        ]

        env_agents: List[Dict[str, Any]] = []
        for key, value in os.environ.items():
            if not (key.startswith("AGENT_") and key.endswith("_TYPE")):
                continue

            raw_name = key[len("AGENT_") : -len("_TYPE")]
            agent_name = raw_name.lower()
            agent_type = value.strip().lower()
            env_agents.append(
                {
                    "name": agent_name,
                    "type": agent_type,
                    "source": "env",
                    "has_api_key": bool(os.getenv(f"AGENT_{raw_name}_API_KEY", "")),
                    "has_base_url": bool(os.getenv(f"AGENT_{raw_name}_BASE_URL", "")),
                    "has_model": bool(os.getenv(f"AGENT_{raw_name}_MODEL", "")),
                }
            )

        env_agents.sort(key=lambda item: item["name"])
        return builtin_agents + env_agents

    @staticmethod
    def _build_openai_compatible(config: Dict[str, Any]) -> AIProvider:
        api_key = config.get("api_key")
        model = config.get("model")
        base_url = config.get("base_url")

        if not api_key:
            raise ValueError("Missing api_key for openai_compatible agent")
        if not model:
            raise ValueError("Missing model for openai_compatible agent")
        if not base_url:
            raise ValueError("Missing base_url for openai_compatible agent")

        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)

    @staticmethod
    def _build_from_env(agent_name: str) -> Optional[AIProvider]:
        env_key = agent_name.upper().replace("-", "_")
        agent_type = os.getenv(f"AGENT_{env_key}_TYPE", "").strip().lower()

        if not agent_type:
            return None

        config = {
            "api_key": os.getenv(f"AGENT_{env_key}_API_KEY", ""),
            "base_url": os.getenv(f"AGENT_{env_key}_BASE_URL", ""),
            "model": os.getenv(f"AGENT_{env_key}_MODEL", ""),
        }

        builders = {
            "gemini": AIProviderFactory._build_gemini,
            "openai": AIProviderFactory._build_openai,
            "openai_compatible": AIProviderFactory._build_openai_compatible,
            "local_http": AIProviderFactory._build_local_http,
            "lightonocr": AIProviderFactory._build_lightonocr,
        }

        build_fn = builders.get(agent_type)
        if not build_fn:
            raise ValueError(
                f"Unsupported AGENT_{env_key}_TYPE: {agent_type}. Supported: gemini, openai, openai_compatible, local_http"
            )

        return build_fn(config)

    @staticmethod
    def get_provider(
        agent_name: str, agent_config: Optional[Dict[str, Any]] = None
    ) -> AIProvider:
        normalized_agent = (agent_name or settings.DEFAULT_PROVIDER).strip().lower()
        config = agent_config or {}

        builders = {
            "gemini": AIProviderFactory._build_gemini,
            "openai": AIProviderFactory._build_openai,
            "openai_compatible": AIProviderFactory._build_openai_compatible,
            "local_http": AIProviderFactory._build_local_http,
            "lightonocr": AIProviderFactory._build_lightonocr,
        }

        if normalized_agent in builders:
            return builders[normalized_agent](config)

        env_provider = AIProviderFactory._build_from_env(normalized_agent)
        if env_provider:
            return env_provider

        # Fallback: treat unknown agents as OpenAI-compatible if full runtime config is provided.
        if all(config.get(k) for k in ("api_key", "base_url", "model")):
            return AIProviderFactory._build_openai_compatible(config)

        raise ValueError(
            f"Unknown agent: {agent_name}. Supported: gemini, openai, openai_compatible, local_http, or env-configured AGENT_<NAME>_*"
        )
