# Extract-PDF API

Service trích xuất bảng dữ liệu / structured text từ ảnh, hỗ trợ nhiều AI agent qua một API thống nhất.

## Mục lục tài liệu

| Tài liệu                                             | Mô tả                                |
| ---------------------------------------------------- | ------------------------------------ |
| [Cài đặt](doc/installation.md)                       | Môi trường Conda, requirements       |
| [Cấu hình](doc/configuration.md)                     | Biến môi trường, env vars, UI config |
| [Khởi động hệ thống](doc/runbook.md)                 | Chạy local (Conda)                   |
| [Chạy bằng Docker](doc/docker-run.md)                | Docker Compose — CPU & GPU           |
| [API & Agent](doc/api-reference.md)                  | Endpoints, schema, ví dụ             |
| [Kiến trúc Provider](doc/architecture.md)            | Cấu trúc code providers              |
| [CLI usage](doc/cli-usage.md)                        | Chạy script dòng lệnh                |
| [Tích hợp plugin web](doc/plugin-integration.md)     | Nhúng API vào web khác               |
| [Mẫu React/Next.js](doc/react-nextjs-integration.md) | Frontend integration                 |
| [Vận hành & Troubleshooting](doc/operations.md)      | Log, lỗi thường gặp                  |

---

## Quick Start

### Chạy bằng Docker (khuyến nghị)

```bash
# 1. Tạo .env từ mẫu
cp .env.example .env
# Điền GOOGLE_API_KEY hoặc giữ AI_PROVIDER=lightonocr

# 2. Khởi động extract-pdf + LightOnOCR cùng nhau
docker compose --profile lightonocr up -d --build

# 3. Mở UI
# http://localhost:8000/ui
```

> ⚠️ **LightOnOCR trên CPU cần ≥ 12 GB RAM cho Docker.**  
> Xem hướng dẫn cấu hình WSL2 trong [doc/docker-run.md](doc/docker-run.md).

### Chạy local (Conda)

```powershell
# Setup 1 lan cho ca extract-pdf + LightOnOCR-2-1B
.\setup-all.ps1

# Tuy chon
.\setup-all.ps1 -Device cpu
.\setup-all.ps1 -PythonVersion 3.10.19 -ForceRecreate
```

Script tren se:

- Tao/cap nhat env Conda cho extract-pdf
- Cai dependencies va model cho LightOnOCR-2-1B

Sau khi setup xong:

```bash
conda activate extract-pdf
python -m app.main
# → http://localhost:8000/ui
```

LightOnOCR chạy riêng:

```bash
conda activate extract-pdf
cd LightOnOCR-2-1B
python api.py
# → http://localhost:7861
```

---

## Endpoints chính

| URL                                 | Mô tả                   |
| ----------------------------------- | ----------------------- |
| `http://localhost:8000/ui`          | Web UI trích xuất       |
| `http://localhost:8000/ui/settings` | Cấu hình agent          |
| `http://localhost:8000/docs`        | Swagger API docs        |
| `http://localhost:7861/`            | LightOnOCR health check |
| `http://localhost:7861/docs`        | LightOnOCR API docs     |

---

## AI Providers hỗ trợ

| Agent               | Mô tả                  | Yêu cầu                        |
| ------------------- | ---------------------- | ------------------------------ |
| `gemini`            | Google Gemini (cloud)  | `GOOGLE_API_KEY`               |
| `openai`            | OpenAI GPT-4o (cloud)  | `OPENAI_API_KEY`               |
| `openai_compatible` | Ollama, vLLM, Azure... | `api_key`, `base_url`, `model` |
| `local_http`        | API HTTP tùy ý (JSON)  | `base_url`                     |
| `lightonocr`        | LightOnOCR-2-1B local  | `LOCAL_HTTP_BASE_URL`          |

Xem chi tiết: [doc/api-reference.md](doc/api-reference.md)
