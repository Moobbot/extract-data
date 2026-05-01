# Cấu hình

## Biến môi trường (`.env`)

Sao chép `.env.example` thành `.env` và điền giá trị:

```bash
cp .env.example .env
```

### Bảng biến môi trường đầy đủ

| Biến                  | Mặc định                        | Mô tả                                                                   |
| --------------------- | ------------------------------- | ----------------------------------------------------------------------- |
| `GOOGLE_API_KEY`      | _(rỗng)_                        | API key cho Gemini provider                                             |
| `OPENAI_API_KEY`      | _(rỗng)_                        | API key cho OpenAI provider                                             |
| `AI_PROVIDER`         | `gemini`                        | Provider mặc định: `gemini` \| `openai` \| `lightonocr` \| `local_http` |
| `OPENAI_MODEL`        | `gpt-4o`                        | Model OpenAI mặc định                                                   |
| `GEMINI_MODEL`        | `gemini-2.5-flash`              | Model Gemini mặc định                                                   |
| `OPENAI_BASE_URL`     | _(rỗng)_                        | Base URL cho OpenAI-compatible API                                      |
| `LOCAL_HTTP_BASE_URL` | `http://localhost:7861/extract` | Endpoint của LightOnOCR API                                             |
| `LOCAL_HTTP_TIMEOUT`  | `300`                           | Timeout (giây) khi gọi local HTTP — CPU cần nhiều hơn                   |
| `CORS_ALLOW_ORIGINS`  | `*`                             | Các origin được phép CORS (phân cách bởi dấu phẩy)                      |
| `API_PORT`            | `8000`                          | Port của extract-pdf API                                                |
| `LOG_LEVEL`           | `INFO`                          | Mức log: `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`                      |

### Ví dụ `.env` cho từng trường hợp

**Dùng LightOnOCR (khuyến nghị):**

```env
AI_PROVIDER=lightonocr
LOCAL_HTTP_BASE_URL=http://lightonocr:7861/extract  # Docker
# LOCAL_HTTP_BASE_URL=http://localhost:7861/extract  # Local
LOCAL_HTTP_TIMEOUT=300
```

**Dùng Gemini:**

```env
AI_PROVIDER=gemini
GOOGLE_API_KEY=AIza...
```

**Dùng OpenAI:**

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

---

## Agent tùy biến qua env

Thêm agent động mà không cần sửa code:

```env
# Khai báo agent tên "qwen" dùng OpenAI-compatible API
AGENT_QWEN_TYPE=openai_compatible
AGENT_QWEN_BASE_URL=http://127.0.0.1:1234/v1
AGENT_QWEN_API_KEY=local
AGENT_QWEN_MODEL=qwen2.5-vl
```

Gọi API với `agent = qwen`.

---

## Cấu hình CORS

Thêm domain frontend vào `CORS_ALLOW_ORIGINS` (phân cách bởi dấu phẩy):

```env
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-app.com
```

Sau khi đổi `.env`, restart API server.

---

## UI config JSON (`ui-config.json`)

- Trang settings: `http://localhost:8000/ui/settings`
- Preset mặc định: `lightonocr` với `base_url = http://localhost:7861/extract`
- Khi chạy Docker: đổi `base_url` sang `http://lightonocr:7861/extract`
- Thay đổi từ Settings UI sẽ được lưu lại vào `ui-config.json`
