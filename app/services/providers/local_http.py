"""
app/services/providers/local_http.py

LocalHTTP provider — gọi API HTTP bất kỳ với payload JSON + base64 ảnh.
Dành cho các mô hình tự host có endpoint nhận JSON.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from app.core.config import settings
from app.services.image_processor import ImageProcessor
from .base import AIProvider


class LocalHTTPProvider(AIProvider):
    """Gọi một HTTP API tùy ý nhận JSON payload chứa image_base64.

    Payload gửi đi:
        {
            "image_base64": "<base64>",
            "prompt": "<prompt>",
            "model": "<model>"  # tùy chọn
        }
    """

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        if not endpoint:
            raise ValueError(
                "[LocalHTTP] Thiếu endpoint URL.\n"
                "Cấu hình base_url trong ui-config.json hoặc LOCAL_HTTP_BASE_URL trong .env."
            )
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = settings.DEFAULT_LOCAL_HTTP_TIMEOUT

    def generate_content(self, image_path: str, prompt: str) -> str:
        base64_image = ImageProcessor.encode_image_base64(image_path)

        payload: dict = {"image_base64": base64_image, "prompt": prompt}
        if self.model:
            payload["model"] = self.model

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            url=self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"[LocalHTTP] HTTP {e.code} từ {self.endpoint}: {body}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"[LocalHTTP] Không kết nối được tới {self.endpoint}: {e.reason}"
            ) from e
        except TimeoutError:
            raise RuntimeError(
                f"[LocalHTTP] Timeout sau {self.timeout}s khi gọi {self.endpoint}.\n"
                "Tăng LOCAL_HTTP_TIMEOUT trong .env nếu cần."
            )

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        # Trích xuất text từ response JSON (hỗ trợ nhiều format)
        from .factory import AIProviderFactory
        return AIProviderFactory.extract_text_from_response(parsed)
