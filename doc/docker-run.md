# Chạy bằng Docker

## Tổng quan services

| Service      | Port | Mô tả                                          |
| ------------ | ---- | ---------------------------------------------- |
| `api`        | 8000 | FastAPI extract-pdf (luôn chạy)                |
| `lightonocr` | 7861 | LightOnOCR-2-1B REST API (profile: lightonocr) |

> Redis và Celery worker đã được loại bỏ. Hệ thống dùng FastAPI `BackgroundTasks` + SQLite.

---

## Điều kiện tiên quyết

- Docker Desktop (hoặc Docker Engine + Compose plugin)
- File `.env` ở root project — xem [configuration.md](configuration.md)
- **Nếu dùng GPU:** [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- **Nếu chạy LightOnOCR trên CPU:** Docker cần ≥ 12 GB RAM — xem hướng dẫn WSL2 bên dưới

---

## Chạy hệ thống

### Phương án 1 — extract-pdf + LightOnOCR (Docker, khuyến nghị)

```bash
docker compose --profile lightonocr up -d --build
```

Services khởi động:

- `api:8000` — extract-pdf API
- `lightonocr:7861` — LightOnOCR API

extract-pdf kết nối tới LightOnOCR qua Docker network: `http://lightonocr:7861/extract`

### Phương án 2 — Chỉ extract-pdf trong Docker, LightOnOCR local

```bash
# Terminal 1: Extract-pdf trong Docker
docker compose up -d --build

# Terminal 2: LightOnOCR trên host
conda activate extract-pdf
cd LightOnOCR-2-1B
python api.py
```

Trong `.env`:

```env
LOCAL_HTTP_BASE_URL=http://host.docker.internal:7861/extract
```

> `host.docker.internal` — trỏ từ container về host (macOS/Windows).  
> Trên Linux: thay bằng IP thực của host.

### Phương án 3 — LightOnOCR chạy riêng (CPU mode)

Từ thư mục `LightOnOCR-2-1B`:

```bash
# CPU (không cần GPU)
docker compose -f docker-compose.cpu.yml up -d --build

# GPU (cần nvidia-container-toolkit)
docker compose up -d --build
```

Rồi chạy extract-pdf bình thường:

```bash
cd ..
docker compose up -d --build
```

---

## Yêu cầu RAM cho LightOnOCR CPU mode

| Giai đoạn               | RAM cần     |
| ----------------------- | ----------- |
| Model weights (float32) | ~4.6 GB     |
| KV cache khi inference  | ~1.8 GB     |
| OS + Docker overhead    | ~0.5 GB     |
| **Tổng tối thiểu**      | **~7 GB**   |
| **Khuyến nghị Docker**  | **≥ 12 GB** |

### Cấu hình WSL2 (Windows)

Tạo/sửa `C:\Users\<user>\.wslconfig`:

```ini
[wsl2]
memory=12GB
processors=4
swap=8GB
```

Áp dụng:

```powershell
wsl --shutdown
# Mở lại Docker Desktop
docker info --format "{{.MemTotal}}"
# Kết quả mong đợi: ≥ 12548165632
```

---

## Kiểm tra trạng thái

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f lightonocr
```

### Các URL sau khi khởi động

| URL                                 | Mô tả                    |
| ----------------------------------- | ------------------------ |
| `http://localhost:8000/`            | Extract-pdf health check |
| `http://localhost:8000/ui`          | Web UI trích xuất        |
| `http://localhost:8000/ui/settings` | Cấu hình agent           |
| `http://localhost:8000/docs`        | Swagger API docs         |
| `http://localhost:7861/`            | LightOnOCR health check  |
| `http://localhost:7861/docs`        | LightOnOCR API docs      |

---

## Lưu ý endpoint LightOnOCR (quan trọng)

Khi `lightonocr` chạy trong Docker Compose, `api` phải dùng tên service để kết nối:

```env
# ✅ Đúng (Docker network)
LOCAL_HTTP_BASE_URL=http://lightonocr:7861/extract

# ❌ Sai (127.0.0.1 trong container = container chính nó)
LOCAL_HTTP_BASE_URL=http://127.0.0.1:7861/extract
```

Kiểm tra endpoint đang dùng:

```bash
docker compose exec api env | grep LOCAL_HTTP_BASE_URL
```

---

## Dừng hệ thống

```bash
docker compose down
```

---

## Troubleshooting nhanh

| Vấn đề                          | Nguyên nhân                 | Cách sửa                                      |
| ------------------------------- | --------------------------- | --------------------------------------------- |
| LightOnOCR tự restart khi OCR   | OOM — thiếu RAM             | Tăng WSL2 memory lên ≥ 12 GB                  |
| `Connection refused`            | Container chưa chạy         | `docker compose ps` kiểm tra                  |
| `Name not known` (hostname lỗi) | Dùng localhost trong Docker | Đổi sang `http://lightonocr:7861/extract`     |
| Timeout khi OCR                 | CPU chậm                    | Tăng `LOCAL_HTTP_TIMEOUT=300`                 |
| `lightonocr` chưa healthy       | Model đang load             | Chờ ~60s, `docker compose logs -f lightonocr` |
