"""
app/services/providers/gemini.py

Google Gemini provider — gọi Gemini API với danh sách model fallback.
"""

from __future__ import annotations

from typing import List, Optional

from PIL import Image
from google import genai

from app.core.config import settings
from .base import AIProvider


class GeminiProvider(AIProvider):
    """Gọi Google Gemini API để trích xuất nội dung từ ảnh.

    Tự động thử nhiều model theo thứ tự ưu tiên nếu model trước thất bại.
    """

    # Danh sách model mặc định theo thứ tự ưu tiên
    DEFAULT_MODELS = [
        settings.DEFAULT_GEMINI_MODEL,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-2.5-pro",
        "gemini-pro-latest",
        "gemini-1.5-flash",
    ]

    def __init__(
        self,
        api_key: str,
        model_candidates: Optional[List[str]] = None,
    ) -> None:
        if not api_key:
            raise ValueError(
                "[Gemini] Google API Key bị thiếu.\n"
                "Thêm GOOGLE_API_KEY vào file .env."
            )
        self.client = genai.Client(api_key=api_key)
        self.model_candidates = model_candidates or self.DEFAULT_MODELS

    def generate_content(self, image_path: str, prompt: str) -> str:
        img = Image.open(image_path)
        last_err: Exception | None = None

        for model in self.model_candidates:
            try:
                resp = self.client.models.generate_content(
                    model=model,
                    contents=[prompt, img],
                )
                return resp.text
            except Exception as e:
                last_err = e

        raise RuntimeError(
            f"[Gemini] Tất cả model đều thất bại.\n"
            f"Đã thử: {self.model_candidates}\n"
            f"Lỗi cuối: {last_err}"
        )
