# Khoi dong he thong

Neu ban chay bang container, xem them [docker-run.md](docker-run.md).

## API server

```bash
conda activate extract-pdf
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Celery worker

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

## Kiem tra endpoint

- Health: `http://127.0.0.1:8000/`
- Docs: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

## Quick UI

- `http://127.0.0.1:8000/ui`
- `http://127.0.0.1:8000/ui/settings`
- Co cac nut: submit task, download JSON, download Excel, copy content, clear.
- De tai JSON/Excel, bat tuy chon `Save output files` truoc khi submit.
- Preset UI duoc luu trong `ui-config.json` va se nap mac dinh LightOnOCR-2-1B.
