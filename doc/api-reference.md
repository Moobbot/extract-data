# API Reference

## Endpoints

| Method | Path                                             | Mô tả                                   |
| ------ | ------------------------------------------------ | --------------------------------------- |
| `GET`  | `/api/v1/agents`                                 | Liệt kê tất cả agent có sẵn             |
| `GET`  | `/api/v1/ui-config`                              | Đọc cấu hình UI                         |
| `PUT`  | `/api/v1/ui-config`                              | Cập nhật cấu hình UI                    |
| `POST` | `/api/v1/extract`                                | OCR 1 file (multipart/form-data)        |
| `POST` | `/api/v1/extract/batch`                          | OCR nhiều file                          |
| `POST` | `/api/v1/extract/folder`                         | OCR cả thư mục                          |
| `POST` | `/api/v1/extract/json`                           | OCR qua JSON payload (base64 hoặc path) |
| `GET`  | `/api/v1/task-status/{task_id}`                  | Polling kết quả task                    |
| `GET`  | `/api/v1/tasks`                                  | Lịch sử tất cả task (từ SQLite)         |
| `GET`  | `/api/v1/task-artifact/{task_id}/json`           | Tải file JSON output                    |
| `GET`  | `/api/v1/task-artifact/{task_id}/excel`          | Tải file Excel output                   |
| `GET`  | `/api/v1/task-artifact/{task_id}/excel-lv1`      | Tải Excel level 1                       |
| `GET`  | `/api/v1/task-artifact/{task_id}/excel-template` | Tải Excel template                      |

---

## Luồng xử lý

```
POST /extract (hoặc /extract/json)
    ↓
task_id trả về ngay (status: "pending")
    ↓ (background)
FastAPI BackgroundTask → process_image_task()
    ↓
AIProviderFactory.get_provider(agent)
    ↓
provider.generate_content(image, prompt)
    ↓
Kết quả lưu vào _TASK_RESULTS + SQLite
    ↓
GET /task-status/{task_id} → "SUCCESS" / "FAILURE"
    ↓
GET /task-artifact/{task_id}/json|excel → tải file
```

---

## Schema `/extract/json`

```json
{
  "image_path": null,
  "image_base64": "<base64-string>",
  "filename": "sample.jpg",
  "agent": "lightonocr",
  "output_format": "json",
  "save_to_file": true,
  "template": "default",
  "options": {
    "model": null,
    "base_url": null,
    "api_key": null
  }
}
```

| Field           | Mặc định         | Mô tả                                               |
| --------------- | ---------------- | --------------------------------------------------- |
| `image_path`    | null             | Đường dẫn file local (thay thế cho base64)          |
| `image_base64`  | null             | Chuỗi base64 của ảnh                                |
| `filename`      | null             | Tên file gốc (dùng đặt tên output)                  |
| `agent`         | _(từ ui-config)_ | Tên provider: `gemini`, `openai`, `lightonocr`, ... |
| `output_format` | `markdown`       | `markdown` hoặc `json`                              |
| `save_to_file`  | `false`          | Lưu JSON + Excel ra thư mục `outputs/`              |
| `template`      | `default`        | Template mapping cho loại tài liệu                  |

---

## Chọn agent

### `gemini`

```json
{ "agent": "gemini" }
```

Yêu cầu: `GOOGLE_API_KEY` trong `.env`.

### `openai`

```json
{ "agent": "openai", "options": { "model": "gpt-4o" } }
```

Yêu cầu: `OPENAI_API_KEY` trong `.env`.

### `openai_compatible` (Ollama, vLLM, Azure...)

```json
{
  "agent": "openai_compatible",
  "options": {
    "base_url": "http://127.0.0.1:1234/v1",
    "api_key": "local",
    "model": "qwen2.5-vl"
  }
}
```

### `local_http` (API HTTP bất kỳ — JSON payload)

```json
{
  "agent": "local_http",
  "options": { "base_url": "http://127.0.0.1:7861/extract" }
}
```

Gửi payload: `{ "image_base64": "...", "prompt": "..." }`  
Parse response theo key: `content` → `text` → `result` → `markdown` → `output`.

### `lightonocr` (LightOnOCR-2-1B — multipart/form-data)

```json
{ "agent": "lightonocr" }
```

Gửi file thật qua multipart. Yêu cầu: `LOCAL_HTTP_BASE_URL` trong `.env`.

---

## Agent động từ env

```env
AGENT_QWEN_TYPE=openai_compatible
AGENT_QWEN_BASE_URL=http://127.0.0.1:1234/v1
AGENT_QWEN_API_KEY=local
AGENT_QWEN_MODEL=qwen2.5-vl
```

Gọi với `"agent": "qwen"`. Kiểm tra: `GET /api/v1/agents`.

---

## Polling kết quả

```js
// 1. Submit task
const res = await fetch("http://localhost:8000/api/v1/extract/json", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    image_base64: base64Image,
    filename: "scan.jpg",
    agent: "lightonocr",
    output_format: "json",
    save_to_file: true,
  }),
});
const { task_id } = await res.json();

// 2. Poll status
let result;
while (true) {
  const status = await fetch(
    `http://localhost:8000/api/v1/task-status/${task_id}`,
  );
  const data = await status.json();
  if (data.status === "SUCCESS" || data.status === "FAILURE") {
    result = data;
    break;
  }
  await new Promise((r) => setTimeout(r, 2000));
}

// 3. Tải artifact
if (result.status === "SUCCESS") {
  window.open(`http://localhost:8000/api/v1/task-artifact/${task_id}/excel`);
}
```

---

## Lưu ý production

- Không expose API key trong frontend public — dùng backend proxy nếu cần.
- Cấu hình `CORS_ALLOW_ORIGINS` với domain thực tế trước khi deploy.
- Task result lưu trong memory (`_TASK_RESULTS`) — mất khi restart container.  
  Lịch sử vẫn có trong SQLite (`outputs/tasks.sqlite3`).
