# Van hanh va troubleshooting

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
