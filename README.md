# Extract PDF API

Service trich xuat bang du lieu/structured text tu anh, ho tro nhieu AI agent qua mot API thong nhat.

## Tong quan

- Backend: FastAPI + Celery.
- Mac dinh agent: `gemini`.
- Agent built-in trong `extract-pdf`: `gemini`, `openai`, `openai_compatible`, `local_http`.
- Ho tro agent tuy bien qua env: `AGENT_<NAME>_*`.

## Kien truc tach rieng

- `extract-pdf` la API orchestration.
- `LightOnOCR` la he thong OCR doc lap ben ngoai.
- `extract-pdf` khong co built-in `lightonocr` nua.
- Neu muon goi LightOnOCR, dung adapter generic `local_http` va tro `options.base_url` vao endpoint cua LightOnOCR.

## Luu y ve UI

- `extract-pdf` co them quick UI de team test nhanh: `http://127.0.0.1:8000/ui`.
- UI de test API la Swagger: `http://127.0.0.1:8000/docs`.
- UI cua LightOnOCR nam o project/doc vu rieng cua LightOnOCR.

### Cach dung Quick UI

1. Mo `http://127.0.0.1:8000/ui`.
2. Chon `agent`.
3. Chon anh upload hoac nhap `image_path` local tren may server.
4. Neu can, nhap `model`, `base_url`, `api_key` trong phan options.
5. Bam `Submit Task` va doi UI poll trang thai cho den khi `SUCCESS`.

## Chuan bi moi truong

1. Env `extract-pdf`: chay web API va worker.
2. Env `lightonocr`: chay service/UI LightOnOCR doc lap.

### Env extract-pdf

```bash
conda activate extract-pdf
pip install -r requirements.txt
```

```env
GOOGLE_API_KEY=your_google_key
OPENAI_API_KEY=your_openai_key
AI_PROVIDER=gemini
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-2.5-flash
OPENAI_BASE_URL=
LOCAL_HTTP_TIMEOUT=60
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Chay he thong

### API server

```bash
conda activate extract-pdf
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Celery worker

```bash
conda activate extract-pdf
celery -A app.core.celery_app.celery_app worker --loglevel=info -P solo --concurrency=1
```

Windows note:

- Celery on Windows should run with `solo` pool.
- If logs still show `SpawnPoolWorker`, stop all old Celery processes and start worker again with the command above.

Redis note:

- `extract-pdf` needs Redis running at `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`.
- If Redis is not running, `/extract/*` will accept requests but the worker cannot consume tasks.

### Kiem tra endpoint

- Health: `http://127.0.0.1:8000/`
- Docs: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

## API chinh

- `GET /api/v1/agents`
- `POST /api/v1/extract`
- `POST /api/v1/extract/batch`
- `POST /api/v1/extract/folder`
- `POST /api/v1/extract/json`
- `GET /api/v1/task-status/{task_id}`

## JSON schema cho /extract/json

```json
{
  "image_path": null,
  "image_base64": "<base64-image>",
  "filename": "sample.jpg",
  "agent": "gemini",
  "output_format": "markdown",
  "save_to_file": false,
  "options": {
    "model": null,
    "base_url": null,
    "api_key": null
  }
}
```

## Cach chon agent

### Gemini

- Dat `agent = gemini` hoac bo trong de dung mac dinh.

### OpenAI

- Dat `agent = openai`.
- Co the override `options.model`.

### OpenAI-compatible

- Dat `agent = openai_compatible`.
- Bat buoc co `options.base_url`, `options.api_key`, `options.model`.

### Local HTTP (generic)

- Dat `agent = local_http`.
- Bat buoc co `options.base_url`.
- `options.api_key` la tuy chon.

Adapter gui payload:

- `image_base64`
- `prompt`

Parser uu tien field: `content`, `text`, `result`, `markdown`, `output`.

## Goi LightOnOCR (he ben ngoai)

- Chay LightOnOCR trong env/doc vu rieng.
- Trong `extract-pdf`, goi bang `agent = local_http`.
- Set `options.base_url` toi endpoint OCR cua LightOnOCR.

## Agent tuy bien bang env

```env
AGENT_QWEN_TYPE=openai_compatible
AGENT_QWEN_BASE_URL=http://127.0.0.1:1234/v1
AGENT_QWEN_API_KEY=local
AGENT_QWEN_MODEL=qwen2.5-vl
```

Khi goi API, dung `agent = qwen`.

## CLI local script

```bash
python simple_extractor.py path/to/image.png --agent gemini
python simple_extractor.py path/to/image.png --agent openai --model gpt-4o
python simple_extractor.py path/to/image.png --agent openai_compatible --base-url http://127.0.0.1:1234/v1 --api-key local --model qwen2.5-vl
python simple_extractor.py path/to/image.png --agent local_http --base-url http://127.0.0.1:8080/ocr
```

## Ghi chu van hanh

- Docs cua `extract-pdf` nam tren port API (hien tai la 8000).
- `http://127.0.0.1:8080/docs` co the 404 neu do la OCR service khong expose docs.
