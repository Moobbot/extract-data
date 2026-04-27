# Extract PDF API

Service trich xuat bang du lieu/structured text tu anh, ho tro nhieu AI agent qua mot API thong nhat.

## Muc luc tai lieu

- [Cai dat](doc/installation.md)
- [Cau hinh](doc/configuration.md)
- [Khoi dong he thong](doc/runbook.md)
- [Chay bang Docker](doc/docker-run.md)
- [API va agent](doc/api-reference.md)
- [Tich hop plugin web khac](doc/plugin-integration.md)
- [Mau React/Next.js](doc/react-nextjs-integration.md)
- [CLI usage](doc/cli-usage.md)
- [Van hanh va troubleshooting](doc/operations.md)

## Quick Start

1. Cai dat phu thuoc theo [Cai dat](doc/installation.md).
2. Tao `.env` theo [Cau hinh](doc/configuration.md).
3. Chay API + worker theo [Khoi dong he thong](doc/runbook.md).
   - Lenh nhanh API: `conda activate extract-pdf` va `python -m app.main`.
4. Mo nhanh:

- UI: `http://127.0.0.1:8000/ui`
- Settings: `http://127.0.0.1:8000/ui/settings`
- Swagger: `http://127.0.0.1:8000/docs`

Preset UI config is stored in `ui-config.json` at the repository root.

## Dung LightOnOCR-2-1B (Recommended)

Mac dinh UI su dung `LightOnOCR-2-1B` (model OCR cuc bo co suc manh 83% overall score).

### Setup (Local)

1. Tab 1 — Chay FastAPI + Gradio server LightOnOCR:

   ```bash
   conda activate extract-pdf
   cd LightOnOCR-2-1B
   python app_server.py
   ```

   → API tai `http://127.0.0.1:7860/ocr`

2. Tab 2 — Chay extract-pdf:

   ```bash
   conda activate extract-pdf
   python -m app.main
   ```

   → Webapp tai `http://127.0.0.1:8000/ui`

3. Tren UI, chon preset `lightonocr-2-1b` va submit task.

### Setup (Docker)

Chay ca hai dich vu trong Docker qua orchestration:

```bash
docker compose --profile lightonocr up -d --build
```

→ LightOnOCR API tai `http://127.0.0.1:7861`

Endpoints:

- Extract-pdf UI: `http://127.0.0.1:8000/ui`
- LightOnOCR API root: `http://127.0.0.1:7861/`
- LightOnOCR API docs: `http://127.0.0.1:7861/docs`
- LightOnOCR extract endpoint: `http://127.0.0.1:7861/extract`
  Xem them: [Docker Runbook](doc/docker-run.md) va [LightOnOCR-2-1B README](LightOnOCR-2-1B/README.md#1-fastapi--gradio-server-chay-ca-ui--rest-api)
