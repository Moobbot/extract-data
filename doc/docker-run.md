# Chay bang Docker

## Muc tieu

Dung Docker Compose de chay:

- `redis` (broker/result backend)
- `api` (FastAPI extract-pdf)
- `worker` (Celery async tasks)
- `lightonocr` (LightOnOCR-2-1B REST API) — tùy chọn

## Dieu kien can

- Da cai Docker Desktop (hoac Docker Engine + Compose plugin)
- GPU + nvidia-container-toolkit (tuong tai, nhung khuyến nghị)
- Co file `.env` o root project (tham khao [configuration.md](configuration.md))

## Chay he thong

### Phương án 1: Chạy extract-pdf + LightOnOCR Docker (khuyến nghị)

Chạy cả extract-pdf và LightOnOCR API qua Docker:

```bash
docker compose --profile lightonocr up -d --build
```

Services sẽ start:

- `redis:6379`
- `api:8000` (extract-pdf API)
- `worker` (Celery)
- `lightonocr:7861` (LightOnOCR API)

Extract-pdf sẽ tự động kết nối tới LightOnOCR qua Docker network: `http://lightonocr:7861/extract`

### Phương án 2: Chạy extract-pdf Docker + LightOnOCR host (dễ debug)

Nếu chỉ chạy extract-pdf trong Docker, còn LightOnOCR chạy trên host:

```bash
docker compose up -d --build
```

Sau đó trên host terminal khác:

```bash
conda activate extract-pdf
cd LightOnOCR-2-1B
python api.py
```

Cấu hình extract-pdf để nó biết LightOnOCR host ở đâu. Mở `.env` và thêm:

```env
LOCAL_HTTP_BASE_URL=http://host.docker.internal:7861/extract
```

(Trên macOS/Windows, Docker cung cấp `host.docker.internal` để kết nối tới host. Trên Linux, sử dụng IP host thực tế.)

## Kiem tra trang thai

```bash
docker compose ps
```

Bạn sẽ thấy cột `STATUS` với `(healthy)` cho `redis`, `api`, `worker` khi hệ thống sẵn sàng. `lightonocr` cũng sẽ `(healthy)` nếu được khởi động.

## Kiem tra nhanh

Extract-pdf API:

- Health: `http://127.0.0.1:8000/`
- Swagger docs: `http://127.0.0.1:8000/docs`
- TMU Quick UI: `http://127.0.0.1:8000/ui`
- Settings UI: `http://127.0.0.1:8000/ui/settings`

LightOnOCR API (nếu chạy):

- Health: `http://127.0.0.1:7861/`
- API docs: `http://127.0.0.1:7861/docs`
- POST endpoint: `http://127.0.0.1:7861/extract`

Kiểm tra nhanh kết nối:

```bash
curl http://127.0.0.1:7861/
```

Từ Settings UI → chọn preset `lightonocr-2-1b` → Submit task

## Xem logs

```bash
# Extract-pdf services
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f redis

# LightOnOCR service (nếu chạy)
docker compose logs -f lightonocr
```

## Dung he thong

```bash
docker compose down
```

Nếu muốn xóa volume Redis:

```bash
docker compose down -v
```

## Luu y

- Worker lấy task qua Redis, nên nếu `redis` chưa healthy thì `worker` sẽ chưa sang healthy.
- Healthcheck của worker dùng `celery inspect ping`, vì vậy cần đợi worker khởi động xong (có `start_period`).
- Trên Windows host, worker trong container Linux không cần `-P solo`.
- File `ui-config.json` được mount vào cả `api` và `worker`, nên thay đổi từ trang settings sẽ được giữ lại trên host.
- LightOnOCR service (nếu chạy) cần khoảng 60 giây để load model — kiên nhẫn chờ `(healthy)` trước khi submit task.
