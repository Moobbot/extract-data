# Trien khai Docker

Tai lieu nay huong dan trien khai extract-pdf + LightOnOCR bang Docker Compose.

## 1) Yeu cau

- Docker Desktop (hoac Docker Engine + Compose plugin)
- File `.env` tai thu muc goc project
- Neu chay GPU: cai `nvidia-container-toolkit`

Khuyen nghi tai nguyen:

- Docker CPU mode cho LightOnOCR: cap RAM Docker/WSL2 >= 12 GB
- Dung luong trong >= 20 GB cho image + model volume

## 2) Chuan bi `.env`

```bash
cp .env.example .env
```

Truong hop chay ca 2 service trong Docker Compose, dung:

```env
LOCAL_HTTP_BASE_URL=http://lightonocr:7861/extract
```

## 3) Khoi dong nhanh

```bash
docker compose --profile lightonocr up -d --build
```

Lenh tren se chay:

- `api` tren port 8000
- `lightonocr` tren port 7861

## 4) Khoi dong qua script start

Script tu chon compose file theo `LIGHTONOCR_DEVICE` trong `.env`.

Windows:

```powershell
.\start.ps1
```

Linux/macOS:

```bash
./start.sh
```

Lenh quan ly:

Windows:

```powershell
.\start.ps1 logs
.\start.ps1 ps
.\start.ps1 down
```

Linux/macOS:

```bash
./start.sh logs
./start.sh ps
./start.sh down
```

## 5) Chay API trong Docker + LightOnOCR tren host (tuy chon)

Neu chi chay `api` trong Docker va chay LightOnOCR tren may host:

1. Chay API:

```bash
docker compose up -d --build
```

2. Chay LightOnOCR local tren host:

```bash
conda activate extract-pdf
cd LightOnOCR-2-1B
python api.py
```

3. Sua `.env` cua API:

```env
LOCAL_HTTP_BASE_URL=http://host.docker.internal:7861/extract
```

Tren Linux, thay `host.docker.internal` bang IP host that.

## 6) Kiem tra trang thai

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f lightonocr
```

URL sau khi khoi dong:

- http://localhost:8000/
- http://localhost:8000/ui
- http://localhost:8000/docs
- http://localhost:7861/
- http://localhost:7861/docs

## 7) Troubleshooting

1. LightOnOCR restart lien tuc tren CPU

- Nguyen nhan: OOM. Tang RAM Docker/WSL2 >= 12 GB.

2. `Connection refused` hoac `Name not known`

- Kiem tra endpoint `LOCAL_HTTP_BASE_URL`.
- Trong container network, khong dung `127.0.0.1` de goi `lightonocr`.

3. Chua healthy ngay sau khi start

- Container dang load model. Theo doi log va cho them 30-60 giay.
