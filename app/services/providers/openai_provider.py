"""
app/services/providers/openai_provider.py

OpenAI (và OpenAI-compatible) provider — gọi chat completions API với vision.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.image_processor import ImageProcessor
from .base import AIProvider

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment]


class OpenAIProvider(AIProvider):
    """Gọi OpenAI (hoặc API tương thích OpenAI) để trích xuất nội dung từ ảnh.

    Hỗ trợ:
      - OpenAI API (gpt-4o, gpt-4-vision, ...)
      - OpenAI-compatible APIs (Ollama, vLLM, Azure, ...)
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
        max_tokens: int = 4096,
    ) -> None:
        if not OpenAI:
            raise ImportError(
                "[OpenAI] Thư viện openai chưa được cài.\n"
                "Chạy: pip install openai"
            )
        if not api_key:
            raise ValueError(
                "[OpenAI] API Key bị thiếu.\n"
                "Thêm OPENAI_API_KEY vào file .env."
            )

        self.model = model
        self.max_tokens = max_tokens

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
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(
                f"[OpenAI] Gọi API thất bại (model={self.model}): {e}"
            ) from e
