# Trien khai Local (khong Docker)

Tai lieu nay huong dan tu cai dat toi chay he thong tren may local bang Python + Conda.

## 1) Cai Python 3.10 (tu may moi)

### Windows

1. Tai Python 3.10 tu https://www.python.org/downloads/.
2. Chay installer va tick `Add python.exe to PATH`.
3. Mo PowerShell moi va kiem tra:

```powershell
python --version
pip --version
```

Neu hien Python 3.10.x la dat.

### macOS

Kiem tra truoc:

```bash
python3 --version
pip3 --version
```

Neu chua co 3.10, cai tu python.org hoac bang Homebrew:

```bash
brew install python@3.10
python3.10 --version
```

### Linux (Ubuntu)

Kiem tra truoc:

```bash
python3 --version
pip3 --version
```

Neu chua co 3.10:

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip
python3.10 --version
```

## 2) Cai Conda

Khuyen nghi dung Miniconda: https://docs.conda.io/en/latest/miniconda.html

Sau khi cai, mo terminal moi va kiem tra:

```bash
conda --version
```

Neu terminal bao khong tim thay `conda`:

```bash
conda init
```

Sau do dong/mo lai terminal.

## 3) Yeu cau he thong

- OS: Windows 10/11, Ubuntu 20.04+, macOS 12+
- Python: 3.10
- Conda: Miniconda/Anaconda
- Git

Khuyen nghi phan cung:

| Kich ban                     | CPU       | RAM                               |
| ---------------------------- | --------- | --------------------------------- |
| Chi extract-pdf              | >= 2 core | >= 4 GB                           |
| extract-pdf + LightOnOCR CPU | >= 4 core | >= 8 GB (khuyen nghi 16 GB)       |
| extract-pdf + LightOnOCR GPU | >= 4 core | >= 8 GB + GPU NVIDIA VRAM >= 8 GB |

## 4) Clone project

```bash
git clone <REPO_URL>
cd extract-pdf
```

## 5) Tao file moi truong

Windows:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Neu chay LightOnOCR local, dat:

```env
LOCAL_HTTP_BASE_URL=http://localhost:7861/extract
```

## 6) Setup local cho ca extract-pdf + LightOnOCR (khuyen nghi)

### Windows

```powershell
.\setup-all.ps1
```

Tuy chon:

```powershell
.\setup-all.ps1 -Device cpu
.\setup-all.ps1 -PythonVersion 3.10.19 -ForceRecreate
```

### Linux/macOS

```bash
bash setup-all.sh
```

Tuy chon:

```bash
bash setup-all.sh --cpu
bash setup-all.sh --python 3.10 --force-recreate
```

Script `setup-all` se:

- Tao/cap nhat env `extract-pdf`
- Cai dependency cho extract-pdf
- Cai dependency va model cho LightOnOCR-2-1B

## 7) Cai rieng LightOnOCR local (tuy chon, dung khi debug rieng)

Phan nay dung khi ban muon cai/chay LightOnOCR doc lap, khong phu thuoc script `setup-all`.

### Windows

```powershell
conda activate extract-pdf
cd LightOnOCR-2-1B
.\setup_env.bat --name extract-pdf --python 3.10 --gpu
```

Neu chay CPU:

```powershell
.\setup_env.bat --name extract-pdf --python 3.10 --cpu
```

### Linux/macOS

```bash
conda activate extract-pdf
cd LightOnOCR-2-1B
bash setup_env.sh --name extract-pdf --python 3.10 --gpu
```

Neu chay CPU:

```bash
bash setup_env.sh --name extract-pdf --python 3.10 --cpu
```

Kiem tra nhanh LightOnOCR sau cai dat:

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

## 8) Chay he thong local

### Cach 1: Chay rieng tung service

Terminal 1 (extract-pdf API):

```bash
conda activate extract-pdf
python -m app.main
```

Terminal 2 (LightOnOCR API):

```bash
conda activate extract-pdf
cd LightOnOCR-2-1B
python api.py
```

### Cach 2: Dung script run-local

Windows:

```powershell
.\run-local.ps1 app
.\run-local.ps1 lightonocr
.\run-local.ps1 both
```

Linux/macOS:

```bash
bash run-local.sh app
bash run-local.sh lightonocr
bash run-local.sh both
```

## 9) Cau hinh ket noi extract-pdf -> LightOnOCR local

Trong file `.env` cua extract-pdf, dat:

```env
LOCAL_HTTP_BASE_URL=http://localhost:7861/extract
LOCAL_HTTP_TIMEOUT=300
```

`LOCAL_HTTP_TIMEOUT=300` khuyen nghi cho CPU mode de tranh timeout som.

## 10) Kiem tra sau khi chay

- Extract-PDF UI: http://localhost:8000/ui
- Extract-PDF docs: http://localhost:8000/docs
- LightOnOCR health: http://localhost:7861/
- LightOnOCR docs: http://localhost:7861/docs

## 11) Loi thuong gap

1. `conda: command not found`

- Chay `conda init`, dong/mo lai terminal.

2. OCR timeout tren CPU

- Tang `LOCAL_HTTP_TIMEOUT=300` hoac cao hon trong `.env`.

3. Loi import package app

- Chay `python -m app.main`, khong chay `python app/main.py`.

4. LightOnOCR khong dung duoc GPU

- Kiem tra `torch.cuda.is_available()` co tra ve `True` khong.
- Neu `False`, cai lai dung bo torch CUDA va driver NVIDIA phu hop.
