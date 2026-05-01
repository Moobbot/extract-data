"""
app/services/providers/base.py

Base class cho tất cả AI providers.
Mọi provider phải kế thừa AIProvider và implement generate_content().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Union


class AIProvider(ABC):
    """Abstract base class cho tất cả AI provider.

    generate_content() có thể trả về:
      - str   : kết quả text thuần (Gemini, OpenAI, LocalHTTP)
      - dict  : kết quả có cấu trúc kèm metadata (LightOnOCR)
                {
                    "text": str,
                    "api_json_path": str | None,
                    "api_excel_path": str | None,
                    "base_url": str,
                }
    """

    @abstractmethod
    def generate_content(self, image_path: str, prompt: str) -> Union[str, dict]:
        """Trích xuất nội dung từ ảnh dựa trên prompt.

        Args:
            image_path: Đường dẫn tuyệt đối tới file ảnh (JPG/PNG/PDF).
            prompt: Câu lệnh hướng dẫn AI.

        Returns:
            str hoặc dict chứa kết quả trích xuất.

        Raises:
            RuntimeError: Khi API call thất bại hoặc file không hợp lệ.
        """
        ...
