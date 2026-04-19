# Cai dat

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

## Chuan bi moi truong

1. Env `extract-pdf`: chay web API va worker.
2. Env `lightonocr`: chay service/UI LightOnOCR doc lap.

## Cai dat dependencies

```bash
conda activate extract-pdf
pip install -r requirements.txt
```