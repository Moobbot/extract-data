"""
app/services/providers/lightonocr.py

LightOnOCR-2-1B provider — gọi REST API qua multipart/form-data.
Khác với LocalHTTPProvider (JSON), provider này gửi file thật.
"""

from __future__ import annotations

import json
import mimetypes
import os
import urllib.error
import urllib.request
import uuid
from typing import Optional

from app.core.config import settings
from .base import AIProvider


class LightOnOCRProvider(AIProvider):
    """Gọi LightOnOCR-2-1B REST API (POST /extract) qua multipart/form-data.

    Trả về dict chứa:
        {
            "text": str,              # nội dung OCR
            "api_json_path": str,     # đường dẫn JSON trên server LightOnOCR
            "api_excel_path": str,    # đường dẫn Excel trên server LightOnOCR
            "base_url": str,          # base URL của LightOnOCR API
        }
    """

    def __init__(self, endpoint: Optional[str] = None) -> None:
        self.endpoint = (
            endpoint
            or os.getenv("LOCAL_HTTP_BASE_URL", "http://localhost:7861/extract")
        )
        self.timeout = settings.DEFAULT_LOCAL_HTTP_TIMEOUT

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_multipart(self, image_path: str, prompt: str) -> tuple[bytes, str]:
        """Tạo body multipart/form-data và content-type header.

        Returns:
            (body_bytes, content_type_header)
        """
        boundary = uuid.uuid4().hex

        def _field(name: str, value: str) -> bytes:
            return (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")

        mime_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
        filename = os.path.basename(image_path)

        with open(image_path, "rb") as fh:
            file_bytes = fh.read()

        file_part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8") + file_bytes + b"\r\n"

        body = (
            _field("prompt", prompt)
            + _field("page_num", "1")
            + _field("temperature", str(settings.DEFAULT_LIGHTONOCR_TEMPERATURE))
            + _field("max_tokens", str(settings.DEFAULT_LIGHTONOCR_MAX_TOKENS))
            + file_part
            + f"--{boundary}--\r\n".encode("utf-8")
        )
        return body, f"multipart/form-data; boundary={boundary}"

    def _classify_http_error(self, code: int, body: str) -> str:
        """Trả về thông báo lỗi chi tiết theo HTTP status code."""
        if code == 400:
            return f"Request không hợp lệ (HTTP 400). Server phản hồi: {body}"
        if code == 404:
            return (
                f"Endpoint không tồn tại (HTTP 404): {self.endpoint}\n"
                "Kiểm tra lại LOCAL_HTTP_BASE_URL trong .env."
            )
        if code == 422:
            return (
                f"Dữ liệu gửi lên không đúng định dạng (HTTP 422): {body}\n"
                "Kiểm tra lại kiểu file ảnh (JPG/PNG/PDF được hỗ trợ)."
            )
        if code == 500:
            return (
                f"LightOnOCR gặp lỗi nội bộ (HTTP 500): {body}\n"
                "Xem log container: docker compose logs -f api"
            )
        if code == 503:
            return (
                "LightOnOCR chưa sẵn sàng (HTTP 503 Service Unavailable).\n"
                "Model có thể đang được load. Chờ vài phút rồi thử lại.\n"
                "Theo dõi: docker compose logs -f api"
            )
        return f"HTTP {code}: {body}"

    def _classify_url_error(self, reason: str) -> str:
        """Trả về thông báo lỗi chi tiết theo loại lỗi mạng."""
        if "Connection refused" in reason:
            return (
                f"Không thể kết nối tới LightOnOCR tại {self.endpoint}\n"
                "→ Container chưa khởi động? Chạy: docker compose -f docker-compose.cpu.yml up -d\n"
                f"→ Endpoint sai? Kiểm tra LOCAL_HTTP_BASE_URL trong .env (hiện tại: {self.endpoint})"
            )
        if "Name or service not known" in reason or "nodename nor servname" in reason:
            return (
                f"Không phân giải được hostname từ {self.endpoint}\n"
                "→ Nếu chạy Docker: container 'lightonocr' chưa chạy hoặc không cùng network.\n"
                "→ Nếu chạy local: đổi LOCAL_HTTP_BASE_URL=http://localhost:7861/extract"
            )
        return f"Lỗi mạng khi gọi LightOnOCR ({self.endpoint}): {reason}"

    # ── Main method ──────────────────────────────────────────────────────────

    def generate_content(self, image_path: str, prompt: str) -> dict:
        filename = os.path.basename(image_path)

        # Kiểm tra file đầu vào
        if not os.path.exists(image_path):
            raise RuntimeError(
                f"[LightOnOCR] File ảnh không tồn tại: {image_path}\n"
                "Kiểm tra lại đường dẫn hoặc thư mục uploaded_images."
            )
        if os.path.getsize(image_path) == 0:
            raise RuntimeError(
                f"[LightOnOCR] File ảnh rỗng (0 bytes): {image_path}\n"
                "File có thể bị lỗi trong quá trình upload."
            )

        # Build request
        body, content_type = self._build_multipart(image_path, prompt)
        req = urllib.request.Request(
            url=self.endpoint,
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )

        # Gọi API
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")

        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="ignore")
            detail = self._classify_http_error(e.code, body_err)
            raise RuntimeError(f"[LightOnOCR] {detail}") from e

        except urllib.error.URLError as e:
            detail = self._classify_url_error(str(e.reason))
            raise RuntimeError(f"[LightOnOCR] {detail}") from e

        except TimeoutError:
            raise RuntimeError(
                f"[LightOnOCR] Timeout sau {self.timeout}s khi xử lý '{filename}'.\n"
                f"→ CPU mode thường mất 60–120 giây/ảnh. Tăng LOCAL_HTTP_TIMEOUT trong .env.\n"
                f"→ Hiện tại: LOCAL_HTTP_TIMEOUT={self.timeout}"
            )

        # Parse kết quả
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # Server trả về text thuần — vẫn dùng được
            return {
                "text": raw,
                "api_json_path": None,
                "api_excel_path": None,
                "base_url": self.endpoint.replace("/extract", ""),
            }

        base_url = self.endpoint.replace("/extract", "")

        # Ưu tiên data có cấu trúc (bảng/kv), fallback sang raw_text
        data = result.get("data")
        if data and isinstance(data, dict) and any(data.values()):
            text_content = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            text_content = (
                result.get("rendered_text")
                or result.get("raw_text")
                or str(result)
            )

        if not text_content or text_content.strip() == "{}":
            raise RuntimeError(
                f"[LightOnOCR] Server trả về kết quả rỗng cho '{filename}'.\n"
                "→ Có thể là trang trắng, ảnh quá mờ, hoặc model không nhận ra nội dung."
            )

        return {
            "text": text_content,
            "api_json_path": result.get("json_path"),
            "api_excel_path": result.get("excel_path"),
            "base_url": base_url,
        }
