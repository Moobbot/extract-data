# Extract-PDF API

Service trich xuat du lieu co cau truc (bang, text, field) tu anh/PDF qua mot API thong nhat.

---

## Tong quan he thong

- Git
- Python 3.10
- Miniconda hoac Anaconda (khuyen nghi)
- Docker Desktop (neu chay bang Docker)

### Yeu cau he dieu hanh (OS)

- Windows 10/11 (khuyen nghi cho script `.ps1`)
- Ubuntu 20.04+ hoac distro Linux tuong duong
- macOS 12+ (Intel/Apple Silicon)

### Yeu cau phan cung

| Kich ban                           | CPU            | RAM                         | GPU/VRAM                                      | O cung trong (uoc tinh) |
| ---------------------------------- | -------------- | --------------------------- | --------------------------------------------- | ----------------------- |
| Chi extract-pdf (khong LightOnOCR) | 2 core tro len | >= 4 GB                     | Khong bat buoc                                | >= 5 GB                 |
| extract-pdf + LightOnOCR (CPU)     | 4 core tro len | >= 8 GB (khuyen nghi 16 GB) | Khong bat buoc                                | >= 20 GB                |
| extract-pdf + LightOnOCR (GPU)     | 4 core tro len | >= 8 GB                     | NVIDIA GPU, VRAM >= 8 GB (khuyen nghi 12 GB+) | >= 20 GB                |

Luu y quan trong khi chay Docker:

- LightOnOCR CPU can cap RAM Docker/WSL2 >= 12 GB de tranh restart do OOM.
- LightOnOCR GPU can cai `nvidia-container-toolkit` (chu yeu tren Linux/WSL2).
- Lan chay dau tien co the tai model, nen can them dung luong o cung cho Docker volume.

## Tai lieu trien khai

- Trien khai local: [doc/deployment-local.md](doc/deployment-local.md)
- Trien khai Docker: [doc/deployment-docker.md](doc/deployment-docker.md)
- Cau hinh bien moi truong: [doc/configuration.md](doc/configuration.md)

---

## Endpoints chinh

| URL                               | Mo ta                    |
| --------------------------------- | ------------------------ |
| http://localhost:8000/            | Health check extract-pdf |
| http://localhost:8000/ui          | Web UI                   |
| http://localhost:8000/ui/settings | Cai dat agent            |
| http://localhost:8000/docs        | Swagger cua extract-pdf  |
| http://localhost:7861/            | Health check LightOnOCR  |
| http://localhost:7861/docs        | Swagger cua LightOnOCR   |

---

## AI providers ho tro

| Provider            | Mo ta                  | Yeu cau                        |
| ------------------- | ---------------------- | ------------------------------ |
| `gemini`            | Google Gemini cloud    | `GOOGLE_API_KEY`               |
| `openai`            | OpenAI cloud           | `OPENAI_API_KEY`               |
| `openai_compatible` | Ollama, vLLM, Azure... | `api_key`, `base_url`, `model` |
| `local_http`        | Goi API HTTP tuy bien  | `base_url`                     |
| `lightonocr`        | LightOnOCR local       | `LOCAL_HTTP_BASE_URL`          |

---

## Tai lieu chi tiet

- [Cau hinh](doc/configuration.md)
- [Trien khai local](doc/deployment-local.md)
- [Trien khai Docker](doc/deployment-docker.md)
- [API reference](doc/api-reference.md)
- [Kien truc](doc/architecture.md)
- [CLI usage](doc/cli-usage.md)
