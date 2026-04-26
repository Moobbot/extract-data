# Van hanh va troubleshooting

## LightOnOCR Integration

### Loi: HTTP 404 hoac "Connection refused"

**Nguyen nhan:** LightOnOCR API server khong dang chay.

**Giai phap:**

1. Kiem tra LightOnOCR API co chay khong:

   ```bash
   curl http://127.0.0.1:7860/health
   ```

   → Nen tra ve:

   ```json
   { "status": "ok", "service": "LightOnOCR-2-1B", "device": "cuda" }
   ```

2. Neu khong co response, khoi dong API:

   ```bash
   conda activate extract-pdf
   cd LightOnOCR-2-1B
   python api_server.py
   ```

3. Kiem tra `ui-config.json` co URL dung khong:
   ```json
   {
     "lightonocr-2-1b": {
       "type": "local_http",
       "base_url": "http://127.0.0.1:7860/ocr",
       "model": null
     }
   }
   ```

### Loi: Model load bi timeout (trang thaiPENDING lau)

**Nguyen nhan:** Model nang (1GB+), may yeu hoac CUDA chua san sang.

**Giai phap:**

1. Kiem tra device dang dung:

   ```bash
   curl http://127.0.0.1:7860/health
   ```

   Neu `"device": "cpu"`, model chay cham. Chuyen sang GPU neu co (kem CUDA 12.x).

2. Chay test nhanh:

   ```bash
   cd LightOnOCR-2-1B
   python -c "from pipeline.model import get_model; m, p = get_model(); print('Model loaded OK')"
   ```

3. Neu vẫn timeout, hãy tăng timeout trong `extract-pdf/.env`:
   ```env
   DEFAULT_LOCAL_HTTP_TIMEOUT=60
   ```

### Loi: Model weights file khong tim thay

**Giai phap:**

1. Check file `model.safetensors` co trong `LightOnOCR-2-1B/` khong:

   ```bash
   ls -la LightOnOCR-2-1B/model.safetensors
   ```

2. Neu khong co, download:
   ```bash
   cd LightOnOCR-2-1B
   python -c "from transformers import AutoModel; AutoModel.from_pretrained('lightonai/LightOnOCR-2-1B')"
   ```

---

## Kiem tra nhanh

- API health: `GET /`
- Swagger: `GET /docs`
- Task status: `GET /api/v1/task-status/{task_id}`

## Worker bi PENDING lau

Neu task giu `PENDING` qua lau:

1. Kiem tra Redis dang chay.
2. Kiem tra Celery worker dang chay.
3. Xem log worker de tim loi ket noi hoac loi provider.

## Windows + Celery

Tren Windows local host, worker nen chay voi `-P solo --concurrency=1` de tranh loi SpawnPool.

## Download JSON/Excel tren Quick UI

- Chon `output_format=json`.
- Bat `Save output files` truoc khi submit.
- Sau khi task `SUCCESS`, nut Download JSON/Excel moi duoc mo.

## Docker

Neu chay bang container, xem [docker-run.md](docker-run.md).
