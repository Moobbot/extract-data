# Chay bang Docker

## Muc tieu

Dung Docker Compose de chay day du 3 service:

- `redis`
- `api` (FastAPI)
- `worker` (Celery)

## Dieu kien can

- Da cai Docker Desktop (hoac Docker Engine + Compose plugin)
- Co file `.env` o root project (tham khao [configuration.md](configuration.md))

## Chay he thong

```bash
docker compose up --build
```

Chay nen:

```bash
docker compose up -d --build
```

## Kiem tra trang thai

```bash
docker compose ps
```

Ban se thay cot `STATUS` kem `(healthy)` cho `redis`, `api`, `worker` khi he thong san sang.

## Kiem tra nhanh API

- Health: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`
- Quick UI: `http://127.0.0.1:8000/ui`
- Settings UI: `http://127.0.0.1:8000/ui/settings`

## Xem logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f redis
```

## Dung he thong

```bash
docker compose down
```

Neu muon xoa volume Redis:

```bash
docker compose down -v
```

## Luu y

- Worker se lay task qua Redis, nen neu `redis` chua healthy thi `worker` se chua sang healthy.
- Healthcheck cua worker dung `celery inspect ping`, vi vay can doi worker khoi dong xong (co `start_period`).
- Tren Windows host, worker trong container Linux khong can `-P solo`.
- File `ui-config.json` duoc mount vao ca `api` va `worker`, nen thay doi tu trang settings se duoc giu lai tren host.
